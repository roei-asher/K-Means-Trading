import numpy as np
from scipy import stats
import logging
from sklearn.cluster import KMeans
from config import get_strategy_min_data_points, get_clustering_params, get_sector_params

# DataFrame column constants for OHLC data
OPEN = 'open'
HIGH = 'high'
LOW = 'low'
CLOSE = 'close'


class Sector:
    """
    Represents a price sector identified by K-means clustering.
    
    Each sector contains statistical properties including KDE-based expected value,
    epsilon (boundary tolerance), and threshold (signal generation threshold).
    """
    def __init__(self, num, min_bound, max_bound, prices, epsilon=None, threshold=None):
        """
        Initialize sector with price boundaries and calculate statistical properties.
        
        Args:
            num: Sector identifier number
            min_bound: Minimum price boundary
            max_bound: Maximum price boundary  
            prices: Array of historical prices within this sector
            epsilon: Boundary tolerance factor (default: 1% of sector range)
            threshold: Signal generation threshold factor (default: 30% of sector range)
        """
        self.num = num
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.size = (max_bound - min_bound) / min_bound if min_bound != 0 else max_bound
        self.prices = prices
        self.median = np.median(prices)
        self.expected_value = self._calculate_expected_value()
        # Get sector parameters from configuration
        sector_config = get_sector_params()
        epsilon_factor = epsilon if epsilon is not None else sector_config.get('epsilon_factor', 0.01)
        threshold_factor = threshold if threshold is not None else sector_config.get('threshold_factor', 0.3)
        
        self.epsilon = epsilon_factor * (max_bound - min_bound)
        self.threshold = threshold_factor * (max_bound - min_bound)

    def _calculate_expected_value(self):
        """Calculate expected value using Kernel Density Estimation integration."""
        kde = stats.gaussian_kde(self.prices)
        x = np.linspace(self.min_bound, self.max_bound, 1000)
        return np.sum(x * kde(x)) / np.sum(kde(x))

    def __contains__(self, price):
        return self.min_bound <= price < self.max_bound

    def calculate_kde(self):
        """Generate KDE probability density function for sector prices."""
        kde = stats.gaussian_kde(self.prices)
        x = np.linspace(self.min_bound, self.max_bound, 200)
        y = kde(x)
        return x, y

class KMeansStrategy:
    """
    Main trading strategy class implementing K-means clustering for price sector analysis.
    
    Automatically determines optimal cluster count, creates price sectors, and generates
    trading signals based on statistical deviation from sector expected values.
    """
    def __init__(self, ticker, data, min_data_points=None):
        """
        Initialize K-means strategy with OHLC data validation.
        
        Args:
            ticker: Stock symbol identifier
            data: Pandas DataFrame with OHLC columns
            min_data_points: Minimum data points required for analysis
        
        Raises:
            ValueError: If insufficient data points provided
        """
        self.ticker = ticker
        # Get minimum data points from configuration
        if min_data_points is None:
            min_data_points = get_strategy_min_data_points()
            
        if data is None or len(data) < min_data_points:
            raise ValueError(f"Insufficient data points for ticker {ticker}. Expected at least {min_data_points}, got {len(data)}.")

        self.df = data
        self.sectors = []
        self.curr_sector = None
        self.num_sectors = 0
        self.median_sectors = []
        self.cluster_labels = None
        self.centroids = None
        self.current_price = self.df[CLOSE].iloc[-1] if not self.df.empty else None
        logging.info(f"Current price for {ticker}: {self.current_price}")

    def _find_optimal_num_clusters(self, data, max_clusters=None):
        """
        Determine optimal cluster count using elbow method with curvature analysis.
        
        Args:
            data: Flattened price data for clustering
            max_clusters: Maximum number of clusters to evaluate
        
        Returns:
            int: Optimal number of clusters based on maximum curvature
        """
        # Get clustering parameters from configuration
        if max_clusters is None:
            clustering_config = get_clustering_params()
            max_clusters = clustering_config.get('max_clusters', 10)
            
        max_k = min(max_clusters, len(data) // 2)
        wcss = []
        # Get clustering algorithm parameters from configuration
        clustering_config = get_clustering_params()
        init_method = clustering_config.get('init_method', 'k-means++')
        random_state = clustering_config.get('random_state', 42)
        n_init = clustering_config.get('n_init', 10)
        
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, init=init_method, random_state=random_state, n_init=n_init)
            kmeans.fit(data)
            wcss.append(kmeans.inertia_)

        # Calculate second derivative (curvature) to find elbow point automatically
        optimal_k = 1
        max_curvature = 0
        for k in range(1, max_k - 1):
            curvature = (wcss[k-1] - 2*wcss[k] + wcss[k+1]) / (1 + (wcss[k] - wcss[k-1])**2)**1.5
            if curvature > max_curvature:
                max_curvature = curvature
                optimal_k = k + 1

        return optimal_k

    def _prepare_data(self):
        """
        Flatten OHLC data for K-means clustering input.
        
        Returns:
            numpy.ndarray: Reshaped price data for clustering algorithm
        
        Raises:
            ValueError: If required OHLC columns missing
            RuntimeError: If data preparation fails
        """
        try:
            # Flatten all OHLC values into single dataset for clustering
            # Note: Amplitude calculation commented out - can be re-enabled for volatility-weighted clustering
            return self.df[[OPEN, HIGH, LOW, CLOSE]].values.flatten().reshape(-1, 1)
        except KeyError as e:
            raise ValueError(f"Missing required column in dataframe: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error preparing data: {str(e)}")

    def divide_into_sectors(self):
        """
        Main clustering method: determines optimal clusters and creates price sectors.
        
        Creates sectors with boundaries based on cluster centroids and populates
        each sector with relevant price data for statistical analysis.
        
        Raises:
            ValueError: If DataFrame is empty
            RuntimeError: If clustering process fails
        """
        try:
            if self.df.empty:
                raise ValueError("DataFrame is empty")
            data = self._prepare_data()
            optimal_k = self._find_optimal_num_clusters(data)
            logging.info(f"Optimal number of clusters for {self.ticker}: {optimal_k}")
            # Use same clustering parameters for final model
            clustering_config = get_clustering_params()
            init_method = clustering_config.get('init_method', 'k-means++')
            random_state = clustering_config.get('random_state', 42)
            n_init = clustering_config.get('n_init', 10)
            
            kmeans = KMeans(n_clusters=optimal_k, init=init_method, random_state=random_state, n_init=n_init)
            self.cluster_labels = kmeans.fit_predict(data)
            logging.debug(f"Cluster labels for {self.ticker}: {self.cluster_labels}")
            # Sort centroids to create ordered price boundaries
            self.centroids = np.sort(kmeans.cluster_centers_, axis=0)
            logging.debug(f"Sorted centroids for {self.ticker}: {self.centroids}")

            # Create sectors with boundaries: centroids act as boundaries between sectors
            for i in range(len(self.centroids) + 1):
                if i == 0:  # First sector: min price to first centroid
                    min_bound = self.df[LOW].min()
                    max_bound = self.centroids[i][0]
                elif i == len(self.centroids):  # Last sector: last centroid to max price
                    min_bound = self.centroids[i-1][0]
                    max_bound = self.df[HIGH].max()
                else:  # Middle sectors: between consecutive centroids
                    min_bound = self.centroids[i-1][0]
                    max_bound = self.centroids[i][0]

                # Extract all OHLC prices that fall within this sector's boundaries
                mask = (self.df[[OPEN, HIGH, LOW, CLOSE]] >= min_bound) & (self.df[[OPEN, HIGH, LOW, CLOSE]] <= max_bound)
                prices = self.df.loc[mask.any(axis=1), [OPEN, HIGH, LOW, CLOSE]].values.flatten()

                if prices.size > 0:
                    logging.info(f"Created sector {i} for {self.ticker}: {min_bound:.2f} - {max_bound:.2f}")
                    self.sectors.append(Sector(i, min_bound, max_bound, prices))

            self.num_sectors = len(self.sectors)
            # Note: Median sector creation disabled for performance - can be re-enabled if needed
            # self._create_median_sectors()
            logging.info(f"Created {self.num_sectors} sectors for {self.ticker}")
            self.update_current_price(self.current_price)  # Identify current price sector
            logging.info(f"Sector division completed for {self.ticker}")
        except Exception as e:
            raise RuntimeError(f"Error dividing into sectors: {str(e)}")

    def _create_median_sectors(self):
        if self.num_sectors < 2:
            return
        elif self.num_sectors == 2:
            self._create_single_median_sector()
        else:
            self._create_multiple_median_sectors()

    def _create_single_median_sector(self):
        min_bound = self.sectors[0].median
        max_bound = self.sectors[1].median
        self._add_median_sector(min_bound, max_bound)

    def _create_multiple_median_sectors(self):
        for i in range(len(self.sectors) + 1):
            if i == 0:
                min_bound = self.df[LOW].min()
                max_bound = self.sectors[i].median
            elif i == len(self.sectors):
                min_bound = self.sectors[i-1].median
                max_bound = self.df[HIGH].max()
            else:
                min_bound = self.sectors[i-1].median
                max_bound = self.sectors[i].median

            self._add_median_sector(min_bound, max_bound)

    def _add_median_sector(self, min_bound, max_bound):
        mask = (self.df[[OPEN, HIGH, LOW, CLOSE]] >= min_bound) & (self.df[[OPEN, HIGH, LOW, CLOSE]] <= max_bound)
        prices = self.df.loc[mask.any(axis=1), [OPEN, HIGH, LOW, CLOSE]].values.flatten()

        if prices.size > 0:
            self.median_sectors.append(Sector(min_bound, max_bound, prices))

    def update_current_price(self, current_price):
        """
        Update current price and identify which sector it belongs to.
        
        Args:
            current_price: Latest price to analyze
        
        Note: Logs warning if price falls outside all defined sectors
        """
        self.current_price = current_price
        logging.debug(f"Updating current price for {self.ticker}: {self.current_price}")
        if self.curr_sector is None or current_price not in self.curr_sector:
            # Find which sector contains the current price
            for sector in self.sectors:
                if current_price in sector:
                    logging.debug(f"Price {current_price} assigned to sector {sector.num} for {self.ticker}")
                    self.curr_sector = sector
                    break
            else:
                logging.warning(f"Current price {current_price} is not in any sector for ticker {self.ticker}")
        logging.debug(f"Price update completed for {self.ticker}")
        # Note: Median sector updates disabled for performance optimization

    def calculate_kde(self):
        all_prices = self.df[[OPEN, HIGH, LOW, CLOSE]].values.flatten()
        kde = stats.gaussian_kde(all_prices)
        x = np.linspace(all_prices.min(), all_prices.max(), 200)
        y = kde(x)
        return x, y

    def calculate_kde(self):
        """Calculate overall KDE for all prices across all sectors."""
        all_prices = self.df[[OPEN, HIGH, LOW, CLOSE]].values.flatten()
        kde = stats.gaussian_kde(all_prices)
        x = np.linspace(all_prices.min(), all_prices.max(), 200)
        y = kde(x)
        return x, y

    def determine_action(self):
        """
        Generate trading signal based on current price position relative to sector statistics.
        
        Returns:
            str: 'BUY', 'SELL', or 'HOLD' based on price deviation from expected value
        
        Logic:
        - HOLD: Price near sector boundaries (within epsilon) to avoid false signals
        - BUY: Price significantly below expected value (exceeds threshold)
        - SELL: Price significantly above expected value (exceeds threshold)
        - HOLD: Price within acceptable deviation range
        """
        if self.current_price is None:
            return "HOLD"  # Default action if processing failed

        # Avoid trading near sector boundaries to prevent false signals
        if abs(self.current_price - self.curr_sector.max_bound) < self.curr_sector.epsilon or \
            abs(self.current_price - self.curr_sector.min_bound) < self.curr_sector.epsilon:
            return "HOLD"
        # Price significantly below expected value - potential buy opportunity
        elif self.curr_sector.expected_value > self.current_price + self.curr_sector.threshold:
            return "BUY"
        # Price significantly above expected value - potential sell opportunity  
        elif self.current_price > self.curr_sector.expected_value + self.curr_sector.threshold:
            return "SELL"
        else:
            return "HOLD"

    def weekly_sectors(self):
        """Convenience method to run sector analysis - typically called weekly."""
        self.divide_into_sectors()
        # self._create_median_sectors()

    def get_sector_statistics(self):
        """Return comprehensive statistics for all sectors including KDE data for visualization."""
        if not self.sectors:
            return []

        return [{
            "num": s.num,
            "min_bound": s.min_bound,
            "max_bound": s.max_bound,
            "median": s.median,
            "expected_value": s.expected_value,
            "epsilon": s.epsilon,
            "threshold": s.threshold,
            "kdeX": s.calculate_kde()[0].tolist(),
            "kdeY": s.calculate_kde()[1].tolist()
        } for s in self.sectors]

    def process_data(self):
        """
        Process and return current sector data for API response.
        
        Returns:
            dict: Current sector statistics or None if processing fails
        """
        try:
            return {
                "centroids": self.centroids.tolist(),
                "sector_min": self.curr_sector.min_bound,
                "sector_max": self.curr_sector.max_bound,
                "expected_value": self.curr_sector.expected_value,
                "epsilon": self.curr_sector.epsilon,
                "threshold": self.curr_sector.threshold
            }
        except Exception as e:
            logging.error(f"Error processing data for ticker {self.ticker}: {str(e)}")
            return None
