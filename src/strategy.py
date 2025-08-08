import numpy as np
from scipy import stats
import logging
from sklearn.cluster import KMeans

# Constants for column names
OPEN = 'open'
HIGH = 'high'
LOW = 'low'
CLOSE = 'close'


class Sector:
    def __init__(self, num, min_bound, max_bound, prices, epsilon=0.01, threshold=0.3):
        self.num = num
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.size = (max_bound - min_bound) / min_bound if min_bound != 0 else max_bound
        self.prices = prices
        self.median = np.median(prices)
        self.expected_value = self._calculate_expected_value()
        self.epsilon = epsilon * (max_bound - min_bound)
        self.threshold = threshold * (max_bound - min_bound)

    def _calculate_expected_value(self):
        kde = stats.gaussian_kde(self.prices)
        x = np.linspace(self.min_bound, self.max_bound, 1000)
        return np.sum(x * kde(x)) / np.sum(kde(x))

    def __contains__(self, price):
        return self.min_bound <= price < self.max_bound

    def calculate_kde(self):
        kde = stats.gaussian_kde(self.prices)
        x = np.linspace(self.min_bound, self.max_bound, 200)
        y = kde(x)
        return x, y

class KMeansStrategy:
    def __init__(self, ticker, data, min_data_points=30):
        self.ticker = ticker
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
        print(self.current_price)

    def _find_optimal_num_clusters(self, data, max_clusters=10):
        max_k = min(max_clusters, len(data) // 2)
        wcss = []
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init=10)
            kmeans.fit(data)
            wcss.append(kmeans.inertia_)

        optimal_k = 1
        max_curvature = 0
        for k in range(1, max_k - 1):
            curvature = (wcss[k-1] - 2*wcss[k] + wcss[k+1]) / (1 + (wcss[k] - wcss[k-1])**2)**1.5
            if curvature > max_curvature:
                max_curvature = curvature
                optimal_k = k + 1

        return optimal_k

    def _prepare_data(self):
        try:
            # self.df['Amplitude'] = np.where(self.df[CLOSE] != self.df[OPEN],
            #                                 ((self.df[HIGH] - self.df[LOW]) / self.df[LOW]) * (
            #                                         (self.df[CLOSE] - self.df[OPEN]) / abs(self.df[CLOSE] - self.df[OPEN])),
            #                                 self.df[HIGH] - self.df[LOW])
            return self.df[[OPEN, HIGH, LOW, CLOSE]].values.flatten().reshape(-1, 1)
        except KeyError as e:
            raise ValueError(f"Missing required column in dataframe: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error preparing data: {str(e)}")

    def divide_into_sectors(self):
        try:
            if self.df.empty:
                raise ValueError("DataFrame is empty")
            data = self._prepare_data()
            optimal_k = self._find_optimal_num_clusters(data)
            print(f"Optimal number of clusters: {optimal_k}")
            kmeans = KMeans(n_clusters=optimal_k, init='k-means++', random_state=42, n_init=10)
            self.cluster_labels = kmeans.fit_predict(data)
            print(f"Cluster labels: {self.cluster_labels}")
            self.centroids = np.sort(kmeans.cluster_centers_, axis=0)
            print(f"Centroids: {self.centroids}")

            for i in range(len(self.centroids) + 1):
                if i == 0:
                    min_bound = self.df[LOW].min()
                    max_bound = self.centroids[i][0]
                elif i == len(self.centroids):
                    min_bound = self.centroids[i-1][0]
                    max_bound = self.df[HIGH].max()
                else:
                    min_bound = self.centroids[i-1][0]
                    max_bound = self.centroids[i][0]

                mask = (self.df[[OPEN, HIGH, LOW, CLOSE]] >= min_bound) & (self.df[[OPEN, HIGH, LOW, CLOSE]] <= max_bound)
                prices = self.df.loc[mask.any(axis=1), [OPEN, HIGH, LOW, CLOSE]].values.flatten()

                if prices.size > 0:
                    print(f"Adding sector: {min_bound} - {max_bound}")
                    self.sectors.append(Sector(i,min_bound, max_bound, prices))

            self.num_sectors = len(self.sectors)
            # COMMENTED MEDIANS FOR NOW TO NOT MAKE IT TOO SLOW
            # self._create_median_sectors()
            print(f"Number of sectors: {self.num_sectors}")
            self.update_current_price(self.current_price) # Update the current sector
            print("finished dividing into sectors")
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
        self.current_price = current_price
        print("self.current_price is", self.current_price)
        if self.curr_sector is None or current_price not in self.curr_sector:
            print("in if statement\n\nsectors are", self.sectors)
            for sector in self.sectors:
                if current_price in sector:
                    print("curr sector is: ", sector)
                    self.curr_sector = sector
                    break
            else:
                logging.warning(f"Current price {current_price} is not in any sector for ticker {self.ticker}")
        print("updated current price with no problems")
        # Update median sectors
        # for median_sector in self.median_sectors:
        #     if current_price in median_sector:
        #         median_sector.update_current_status(True, current_price)
        #     else:
        #         median_sector.update_current_status(False)

    def calculate_kde(self):
        all_prices = self.df[[OPEN, HIGH, LOW, CLOSE]].values.flatten()
        kde = stats.gaussian_kde(all_prices)
        x = np.linspace(all_prices.min(), all_prices.max(), 200)
        y = kde(x)
        return x, y

    def determine_action(self):
        if self.current_price is None:
            return "HOLD"  # Default action if processing failed

        if abs(self.current_price - self.curr_sector.max_bound) < self.curr_sector.epsilon or \
            abs(self.current_price - self.curr_sector.min_bound) < self.curr_sector.epsilon:
            return "HOLD"
        elif self.curr_sector.expected_value > self.current_price + self.curr_sector.threshold:
            return "BUY"
        elif self.current_price > self.curr_sector.expected_value + self.curr_sector.threshold:
            return "SELL"
        else:
            return "HOLD"

    def weekly_sectors(self):
        self.divide_into_sectors()
        # self._create_median_sectors()

    def get_sector_statistics(self):
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
