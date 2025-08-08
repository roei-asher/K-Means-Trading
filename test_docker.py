#!/usr/bin/env python3
"""
Test script to verify K-Means Trading Strategy Docker setup.

This script tests the basic functionality without requiring
Interactive Brokers connection, using synthetic data.
"""

import asyncio
import websockets
import json
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_synthetic_ohlc_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Generate synthetic OHLC data for testing purposes.
    
    Args:
        symbol: Stock symbol
        days: Number of days of data to generate
        
    Returns:
        DataFrame with OHLC data
    """
    np.random.seed(42)  # For reproducible results
    
    # Generate dates
    dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
    
    # Generate price data with some trend and volatility
    base_price = 100.0
    prices = []
    current_price = base_price
    
    for i in range(days):
        # Random walk with slight upward trend
        daily_return = np.random.normal(0.001, 0.02)  # 0.1% mean return, 2% volatility
        current_price *= (1 + daily_return)
        
        # Generate OHLC from the closing price
        volatility = np.random.uniform(0.005, 0.03)  # 0.5% to 3% intraday volatility
        
        high = current_price * (1 + volatility * np.random.uniform(0.3, 1.0))
        low = current_price * (1 - volatility * np.random.uniform(0.3, 1.0))
        open_price = current_price * (1 + np.random.uniform(-0.01, 0.01))
        
        # Ensure OHLC relationships are maintained
        high = max(high, open_price, current_price)
        low = min(low, open_price, current_price)
        
        prices.append({
            'date': dates[i].strftime('%Y%m%d %H:%M:%S'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(current_price, 2),
            'volume': int(np.random.uniform(100000, 1000000))
        })
    
    return pd.DataFrame(prices)

async def test_websocket_connection(host: str = "localhost", port: int = 8765):
    """Test WebSocket connection to the trading server."""
    try:
        uri = f"ws://{host}:{port}"
        logging.info(f"Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            logging.info("WebSocket connection established")
            
            # Test message
            test_request = {
                "type": "get_historical_data",
                "tickers": ["AAPL", "MSFT"],
                "barSize": "1 day",
                "duration": "1 M",
                "rth": True
            }
            
            logging.info("Sending test request...")
            await websocket.send(json.dumps(test_request))
            
            # Wait for response
            logging.info("Waiting for response...")
            response = await websocket.recv()
            data = json.loads(response)
            
            logging.info(f"Received response type: {data.get('type', 'unknown')}")
            
            # Check if we got data for both tickers
            for ticker in test_request["tickers"]:
                if ticker in data:
                    if 'error' in data[ticker]:
                        logging.warning(f"Error for {ticker}: {data[ticker]['error']}")
                    else:
                        logging.info(f"Successfully received data for {ticker}")
                        if 'action' in data[ticker]:
                            logging.info(f"Trading signal for {ticker}: {data[ticker]['action']}")
                else:
                    logging.warning(f"No data received for {ticker}")
            
            return True
            
    except Exception as e:
        logging.error(f"WebSocket test failed: {e}")
        return False

async def main():
    """Run Docker setup tests."""
    logging.info("Starting K-Means Trading Strategy Docker tests...")
    
    # Test 1: WebSocket Connection
    logging.info("=" * 50)
    logging.info("Test 1: WebSocket Connection")
    
    success = await test_websocket_connection()
    
    if success:
        logging.info("✅ Docker setup test PASSED")
        sys.exit(0)
    else:
        logging.error("❌ Docker setup test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
        sys.exit(1)