# K-Means Trading Strategy - Development Guide

This guide provides comprehensive information for developers working on the K-Means Trading Strategy project.

## Project Architecture

### Core Components

1. **Strategy Engine** (`src/strategy.py`)
   - `KMeansStrategy`: Main analysis class
   - `Sector`: Price sector representation with statistical properties
   - Implements K-means clustering for price segmentation

2. **Server Backend** (`src/server.py`)
   - `TradingServer`: WebSocket server for real-time communication
   - `IBapi`: Interactive Brokers API wrapper
   - Handles historical data requests and strategy execution

3. **Web Dashboard** (`src/dashboard.html|js|css`)
   - Interactive web interface for strategy visualization
   - Real-time charting with Plotly.js and D3.js
   - Statistical analysis and trading signal display

4. **Configuration System** (`src/config.py`)
   - Centralized configuration management
   - YAML-based configuration with environment overrides
   - Structured access to all system parameters

### Data Flow

```
IB TWS/Gateway → IBapi → TradingServer → KMeansStrategy → WebSocket → Dashboard
     ↑                                        ↓
Configuration ← config.yaml              Results/Signals
```

## Development Setup

### Prerequisites

```bash
# Python 3.9+ with pip
python --version  # Should be 3.9+

# Install development dependencies
pip install -r requirements.txt

# Optional: Development tools
pip install pytest black flake8 mypy
```

### Running Locally

1. **Start Interactive Brokers** (for live data):
   ```bash
   # Start TWS or IB Gateway
   # Enable API connections
   # Note the port (7497 for TWS Paper, 7496 for Gateway)
   ```

2. **Configure the Application**:
   ```bash
   # Copy and modify configuration
   cp config.yaml config.local.yaml
   # Edit IB connection settings, logging levels, etc.
   ```

3. **Start the Server**:
   ```bash
   cd src/
   python server.py
   ```

4. **Open Dashboard**:
   ```bash
   # Option 1: Direct file access
   open dashboard.html

   # Option 2: Simple HTTP server
   python -m http.server 8080
   # Then open http://localhost:8080/dashboard.html

   # Option 3: VS Code Live Server extension
   # Right-click dashboard.html → "Open with Live Server"
   ```

## Code Organization

### Strategy Module (`strategy.py`)

**Key Classes:**

- `Sector`: Represents price clusters with statistical properties
  - KDE-based expected value calculation
  - Dynamic epsilon and threshold parameters
  - Boundary detection and containment checks

- `KMeansStrategy`: Main trading strategy implementation
  - Automatic optimal cluster detection (elbow method)
  - OHLC data preparation and clustering
  - Trading signal generation logic

**Key Methods:**

- `_find_optimal_num_clusters()`: Elbow method with curvature analysis
- `divide_into_sectors()`: Primary clustering and sector creation
- `determine_action()`: Trading signal generation
- `get_sector_statistics()`: Visualization data export

### Server Module (`server.py`)

**Key Classes:**

- `IBapi`: Interactive Brokers API wrapper
  - Handles historical data requests
  - Thread-safe event synchronization
  - Data format conversion

- `TradingServer`: WebSocket server implementation
  - Client connection management
  - Request routing and processing
  - Strategy integration and response formatting

### Configuration System (`config.py`)

**Features:**

- Hierarchical YAML configuration structure
- Environment variable override support
- Type-safe configuration access
- Default fallback values

**Usage Examples:**

```python
from config import config, get_strategy_min_data_points

# Direct access
min_points = config.get('strategy', 'min_data_points', default=30)

# Convenience functions
clustering_params = get_clustering_params()
ib_settings = get_ib_connection_params()
```

## Configuration Reference

### Strategy Parameters

```yaml
strategy:
  min_data_points: 30          # Minimum bars required for analysis
  clustering:
    max_clusters: 10           # Maximum K for elbow method
    init_method: "k-means++"   # Initialization algorithm
    random_state: 42           # Reproducibility seed
    n_init: 10                 # Number of random initializations
  sectors:
    epsilon_factor: 0.01       # Boundary tolerance (1% of range)
    threshold_factor: 0.3      # Signal threshold (30% of range)
```

### Interactive Brokers Settings

```yaml
interactive_brokers:
  connection:
    host: "127.0.0.1"         # TWS/Gateway host
    port: 7497                # TWS port (7496 for Gateway)
    client_id: 1              # API client identifier
  data_request:
    default_duration: "1 M"   # Historical data period
    default_bar_size: "1 day" # Bar interval
    default_rth: true         # Regular trading hours only
    request_timeout: 50       # Data request timeout (seconds)
```

### Performance Tuning

```yaml
performance:
  enable_median_sectors: false    # Disable for better performance
  memory:
    cleanup_ib_data: true        # Clean up after processing
    max_data_retention_mb: 100   # Memory limit per request
```

## Testing

### Unit Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ --cov-report=html

# Run specific test file
pytest tests/test_strategy.py
```

### Integration Testing

```bash
# Test with mock data (no IB connection required)
python test_docker.py

# Test WebSocket connection
python -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('ws://localhost:8765'):
        print('WebSocket OK')
asyncio.run(test())
"
```

### Performance Testing

```bash
# Memory profiling
python -m memory_profiler src/strategy.py

# Timing analysis
python -m cProfile -o profile_stats.prof src/server.py
```

## Code Style and Standards

### Python Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Docstrings for all public methods
- Maximum line length: 100 characters

**Example:**
```python
def calculate_expected_value(self, prices: np.ndarray) -> float:
    """
    Calculate expected value using KDE integration.

    Args:
        prices: Array of historical prices

    Returns:
        KDE-based expected value
    """
    kde = stats.gaussian_kde(prices)
    x = np.linspace(prices.min(), prices.max(), 1000)
    return np.sum(x * kde(x)) / np.sum(kde(x))
```

### JavaScript Code Style

- Use ES6+ features
- Consistent indentation (2 spaces)
- Descriptive variable names
- Modular function organization

### Documentation Standards

- Comprehensive docstrings for all classes and methods
- Inline comments for complex algorithms
- Configuration parameter documentation
- Architecture diagrams for complex flows

## Debugging

### Common Development Issues

1. **Import Errors**:
   ```bash
   # Ensure PYTHONPATH includes src/
   export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
   ```

2. **IB Connection Issues**:
   ```bash
   # Test IB connection directly
   python -c "
   from ibapi.client import EClient
   from ibapi.wrapper import EWrapper
   class TestApp(EWrapper, EClient):
       def __init__(self):
           EClient.__init__(self, self)
   app = TestApp()
   app.connect('127.0.0.1', 7497, 1)
   print('Connection test completed')
   "
   ```

3. **Configuration Loading**:
   ```bash
   # Test configuration loading
   python -c "
   from config import config
   print('Config loaded:', config.config.keys())
   print('Strategy config:', config.get_strategy_config())
   "
   ```

### Logging Configuration

```python
import logging

# Development logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

### Debugging Tools

1. **Python Debugger (pdb)**:
   ```python
   import pdb; pdb.set_trace()  # Breakpoint
   ```

2. **WebSocket Debugging**:
   ```bash
   # Use wscat for WebSocket testing
   npm install -g wscat
   wscat -c ws://localhost:8765
   ```

3. **Network Analysis**:
   ```bash
   # Monitor network connections
   netstat -an | grep :8765

   # Packet capture
   tcpdump -i lo -A 'port 8765'
   ```

## Contributing

### Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone <your-fork-url>
   cd kmeans_trading
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Development**:
   - Write code following style guidelines
   - Add comprehensive tests
   - Update documentation

4. **Testing**:
   ```bash
   # Run full test suite
   pytest
   black src/
   flake8 src/
   ```

5. **Commit and Push**:
   ```bash
   git add .
   git commit -m "feat: descriptive commit message"
   git push origin feature/your-feature-name
   ```

6. **Pull Request**:
   - Create PR with detailed description
   - Include test results and performance impact
   - Request review from maintainers

### Code Review Guidelines

- **Functionality**: Does the code work as intended?
- **Performance**: Are there performance implications?
- **Security**: Are there security considerations?
- **Documentation**: Is the code well-documented?
- **Testing**: Are there adequate tests?

## Advanced Topics

### Custom Strategy Development

To implement a custom trading strategy:

1. **Extend Base Classes**:
   ```python
   from strategy import KMeansStrategy

   class CustomStrategy(KMeansStrategy):
       def determine_action(self):
           # Custom signal generation logic
           return "CUSTOM_SIGNAL"
   ```

2. **Add Configuration Support**:
   ```yaml
   # config.yaml
   custom_strategy:
     custom_param: value
   ```

3. **Integration**:
   ```python
   # server.py
   strategy = CustomStrategy(symbol, df)
   ```

### Performance Optimization

1. **Vectorization**:
   ```python
   # Use NumPy operations instead of loops
   prices_vectorized = df[['open', 'high', 'low', 'close']].values.flatten()
   ```

2. **Caching**:
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def expensive_calculation(self, data_hash):
       # Cache expensive operations
       pass
   ```

3. **Async Processing**:
   ```python
   async def process_multiple_symbols(symbols):
       tasks = [process_symbol(symbol) for symbol in symbols]
       return await asyncio.gather(*tasks)
   ```

### Deployment Patterns

1. **Development**: Local Python + file-based dashboard
2. **Testing**: Docker containers + mock data
3. **Staging**: Docker Compose + IB Paper Trading
4. **Production**: Kubernetes + IB Live Trading + monitoring

This development guide provides the foundation for contributing to and extending the K-Means Trading Strategy project.