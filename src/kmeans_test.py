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
from kmeans_strategy import KMeansStrategy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = {}
        self.event = threading.Event()

    def historicalData(self, reqId, bar):
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
        super().historicalDataEnd(reqId, start, end)
        self.event.set()

class TradingServer:
    def __init__(self, host="127.0.0.1", port=7497):
        self.clients = set()
        self.host = host
        self.port = port
        self.ib_api = IBapi()
        self.ib_api.connect(self.host, self.port, clientId=1)
        self.ib_thread = threading.Thread(target=self.run_ib, daemon=True)
        self.ib_thread.start()
        self.next_req_id = 1

    def run_ib(self):
        self.ib_api.run()

    def get_historical_data(self, symbol, duration='1 M', bar_size='1 day', rth=True):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'

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

        self.ib_api.event.wait(50)  # Wait up to 50 seconds for data

        if req_id not in self.ib_api.data:
            logging.warning(f"No data received for {symbol}")
            return None

        df = pd.DataFrame(self.ib_api.data[req_id])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        print(df)
        del self.ib_api.data[req_id]
        return df

    async def process_historical_data_request(self, websocket, data):
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
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'get_historical_data':
                    await self.process_historical_data_request(websocket, data)
        finally:
            self.clients.remove(websocket)

async def main():
    server = TradingServer()
    host = "localhost"
    port = 8765
    async with websockets.serve(server.handle_message, host, port):
        logging.info(f"Server started on {host}:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")