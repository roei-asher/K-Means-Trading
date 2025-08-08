import asyncio
import websockets
import json
import logging
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import pandas as pd
import threading
import time
from strategy import KMeansStrategy
from config import config, get_ib_connection_params, get_websocket_params

# Configure logging from configuration file
logging_config = config.get_logging_config()
log_level = getattr(logging, logging_config.get('level', 'INFO').upper())
log_format = logging_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=log_level, format=log_format)

class IBapi(EWrapper, EClient):
    """
    Interactive Brokers API wrapper for historical data retrieval.
    
    Handles connection to TWS/Gateway and processes historical data requests
    with thread-safe event synchronization.
    """
    def __init__(self):
        """Initialize IB API client with data storage and event handling."""
        EClient.__init__(self, self)
        self.data = {}
        self.event = threading.Event()

    def historicalData(self, reqId, bar):
        """Callback for receiving historical bar data from IB API."""
        if reqId not in self.data:
            self.data[reqId] = []
        self.data[reqId].append({
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        })

    def historicalDataEnd(self, reqId, start, end):
        """Callback indicating end of historical data transmission."""
        super().historicalDataEnd(reqId, start, end)
        self.event.set()

class TradingServer:
    """
    WebSocket server for K-means trading strategy analysis.
    
    Integrates Interactive Brokers data feed with real-time web dashboard,
    processing historical data requests and generating trading signals.
    """
    def __init__(self, host=None, port=None):
        """
        Initialize trading server with IB connection.
        
        Args:
            host: IB TWS/Gateway host address
            port: IB TWS/Gateway port (7497 for TWS, 7496 for Gateway)
        """
        self.clients = set()
        
        # Get IB connection parameters from configuration
        ib_config = get_ib_connection_params()
        self.host = host if host is not None else ib_config.get('host', '127.0.0.1')
        self.port = port if port is not None else ib_config.get('port', 7497)
        self.ib_api = IBapi()
        # Get client ID from configuration
        ib_config = get_ib_connection_params()
        client_id = ib_config.get('client_id', 1)
        
        self.ib_api.connect(self.host, self.port, clientId=client_id)
        self.ib_thread = threading.Thread(target=self.run_ib, daemon=True)
        self.ib_thread.start()
        self.next_req_id = 1

    def run_ib(self):
        """Run IB API message loop in dedicated thread."""
        self.ib_api.run()

    def get_historical_data(self, symbol, duration=None, bar_size=None, rth=None):
        """
        Request and retrieve historical data from Interactive Brokers.
        
        Args:
            symbol: Stock ticker symbol
            duration: Historical data period (e.g., '1 M', '1 Y')
            bar_size: Bar interval (e.g., '1 day', '1 hour')
            rth: Regular trading hours only (True/False)
        
        Returns:
            pd.DataFrame: OHLC data with datetime index or None if failed
        """
        # Get default data request parameters from configuration
        ib_config = config.get_ib_config()
        data_config = ib_config.get('data_request', {})
        contract_defaults = ib_config.get('contract_defaults', {})
        
        duration = duration if duration is not None else data_config.get('default_duration', '1 M')
        bar_size = bar_size if bar_size is not None else data_config.get('default_bar_size', '1 day')
        rth = rth if rth is not None else data_config.get('default_rth', True)
        
        # Create stock contract for US equities using configuration defaults
        contract = Contract()
        contract.symbol = symbol
        contract.secType = contract_defaults.get('sec_type', 'STK')
        contract.exchange = contract_defaults.get('exchange', 'SMART')
        contract.currency = contract_defaults.get('currency', 'USD')

        req_id = self.next_req_id
        self.next_req_id += 1

        self.ib_api.event.clear()
        self.ib_api.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=int(rth),
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        # Get request timeout from configuration
        timeout = data_config.get('request_timeout', 50)
        self.ib_api.event.wait(timeout)  # Wait for data response

        if req_id not in self.ib_api.data:
            logging.warning(f"No data received for {symbol}")
            return None

        # Convert to DataFrame with datetime index
        df = pd.DataFrame(self.ib_api.data[req_id])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        logging.info(f"Retrieved {len(df)} bars for {symbol}")
        
        # Clean up stored data to prevent memory leaks (configurable)
        cleanup_enabled = config.get('performance', 'memory', 'cleanup_ib_data', default=True)
        if cleanup_enabled:
            del self.ib_api.data[req_id]
        return df

    async def process_historical_data_request(self, websocket, data):
        """
        Process WebSocket request for historical data analysis.
        
        Retrieves data for each ticker, applies K-means strategy analysis,
        and returns comprehensive results including trading signals.
        
        Args:
            websocket: WebSocket connection for response
            data: Request parameters (tickers, barSize, duration, rth)
        """
        tickers = data['tickers']
        bar_size = data['barSize']
        duration = data['duration']
        rth = data['rth']

        historical_data = {}
        for symbol in tickers:
            try:
                df = self.get_historical_data(symbol, duration, bar_size, rth)
                if df is None or df.empty:
                    raise ValueError(f"No valid data received for {symbol}")

                # Apply K-means clustering analysis to generate trading signals
                strategy = KMeansStrategy(symbol, df)
                strategy.divide_into_sectors()
                action = strategy.determine_action()

                historical_data[symbol] = {
                    'dates': df.index.astype(str).tolist(),
                    'open': df['open'].tolist(),
                    'high': df['high'].tolist(),
                    'low': df['low'].tolist(),
                    'close': df['close'].tolist(),
                    'volume': df['volume'].tolist(),
                    'sectors': strategy.get_sector_statistics(),
                    'action': action
                }
            except Exception as e:
                logging.error(f"Error processing data for {symbol}: {str(e)}")
                historical_data[symbol] = {'error': str(e)}

        response = {
            'type': 'historical_data',
            'tickers': tickers,
            **historical_data
        }

        await websocket.send(json.dumps(response))

    async def handle_message(self, websocket, path):
        """
        Handle incoming WebSocket connections and messages.
        
        Manages client connections and routes requests to appropriate handlers.
        
        Args:
            websocket: WebSocket connection
            path: Request path (unused)
        """
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'get_historical_data':
                    await self.process_historical_data_request(websocket, data)
        finally:
            self.clients.remove(websocket)

async def main():
    """Start the WebSocket server for trading strategy analysis."""
    # Initialize trading server with configuration
    server = TradingServer()
    
    # Get WebSocket server parameters from configuration
    ws_config = get_websocket_params()
    host = ws_config.get('host', 'localhost')
    port = ws_config.get('port', 8765)
    async with websockets.serve(server.handle_message, host, port):
        logging.info(f"Server started on {host}:{port}")
        await asyncio.Future()  # Keep server running indefinitely

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")