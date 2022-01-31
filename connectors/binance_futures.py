import logging
import requests
import time
import typing

from urllib.parse import urlencode
import hmac
import hashlib

import websocket
import json

import threading

from models import *

logger = logging.getLogger()

class BinanceFuturesClient:
    # constructor that gets called automatically upon initialization
    # ask ourselves what does our class need to know from the beginning
    # needs to know: if we're using test or prod,
    def __init__(self, public_key: str, secret_key: str, testnet: bool):
        # if testnet boolean is true then make the base url & WebSocket URL the testnet
        if testnet:
            self._base_url = "https://testnet.binancefuture.com"
            self._wss_url = "wss://stream.binancefuture.com/ws"
        # Otherwise use the production versions of the url's
        else:
            self._base_url = "https://fapi.binance.com"
            self._wss_url = "wss://fstream.binance.com/ws"

        # Global Variables Section that will need to be shared at some point in the class
        self._public_key = public_key
        self._secret_key = secret_key
        self._headers = {'X-MBX-APIKEY': self._public_key}
        self.contracts = self.get_contracts()
        self.balances = self.get_balances()
        # dictionary for prices key for this dictionary will hold a key/value pair k=symbol/v=bid & ask price
        self.prices = dict()

        self.logs = []

        self._ws_id = 1
        self._ws = None

        # if we start the websocket here then our program would et stuck here upon initialization of the client object
        # because start_ws uses a run_forever method creating an infinite loop
        # so what we need to do is create a THREAD for it to run on in parallel with the application so that it runs
        # in the background and will allow our program to do other things
        t = threading.Thread(target=self._start_ws)
        # then we just start it with the next line
        t.start()

        # message to let us know that the client was successfully initialized
        logger.info("Binance Futures Client Successfully Initialized")

    def _add_log(self, msg: str):
        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    # method to generate the signature which takes a self parameter and the dict data
    # The hmac.new() method takes 3 arguments a key, message, and digest mode
    # the hmac.new portion takes the secret_key from your api key set and turns it into a byte type with the encode
    # method appended to it. Then it takes the data turns it into a queryString as stated in the binance api document
    # using the urlencode method with data as it's parameter and turns that whole thing into a byte type using the
    # encode method appended to it. Then the digest mode is the hashlib.sha256 algorithm.
    # Last append the hexdigest() method - not sure about the significance of this part
    def _generate_signature(self, data: typing.Dict) -> str:
        hmac.new
        return hmac.new(self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    # Method to make a request to the binance api
    def _make_request(self, method: str, endpoint: str, data: typing.Dict):
        # If the method used passes the GET parameter create a response variable to hold the actual request to the
        # api and pass the base url being used with the endpoint appended and any other parameter data
        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        # else raise an error
        elif method == "POST":
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        else:
            raise ValueError()
        # if the response code is successful (ie 200) return the json data information back from the endpoint call
        if response.status_code == 200:
            return response.json()
        # else return a formatted error message with useful information about the error
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)",
                         method, endpoint, response.json(), response.status_code)
            return None

    # Method to get the contracts from binance futures. Only has a self parameter
    def get_contracts(self) -> typing.Dict[str, Contract]:
        # variable to hold the entire contracts data requested
        exchange_info = self._make_request("GET", "/fapi/v1/exchangeInfo", dict())
        # variable for contracts initialized to an empty dictionary
        contracts = dict()

        # if the exchange_info request is not None (meaning it didnt error) then loop through it and grab the data for
        # each contract and place it in the contracts dictionary
        if exchange_info is not None:
            for contract_data in exchange_info['symbols']:
                contracts[contract_data['symbol']] = Contract(contract_data, "binance")
        # return the contracts dictionary
        return contracts

    def get_historical_candles(self, contract: Contract, interval: str) -> typing.List[Candle]:
        # variable to hold a dictionary for the data
        data = dict()
        # data will have 3 key/value pairs; symbol, interval, and limit. Limit is hard coded at 1000.
        data['symbol'] = contract.symbol
        data['interval'] = interval
        data['limit'] = 1000
        # variable to hold the data from the request
        raw_candles = self._make_request("GET", "/fapi/v1/klines", data)
        # initialize variable candles to an empty array that we will append the data from raw_candles into
        candles = []

        # if the raw_candles request is not None (meaning it didnt error) then loop through it and grab the data for
        # each contract and place it in the candles dictionary
        if raw_candles is not None:
            for c in raw_candles:
                candles.append(Candle(c, interval, "binance"))
                print(c)

        return candles

    def get_bid_ask(self, contract: Contract) -> typing.Dict[str, float]:
        data = dict()
        data['symbol'] = contract.symbol
        ob_data = self._make_request("GET", "/fapi/v1/ticker/bookTicker", data)

        # if the ob_data request is not None (meaning it didnt error) then loop through it and grab the data for
        # each contract and place it in the prices dictionary
        if ob_data is not None:
            # if the symbol does not already exist in self.prices add it with it's corresponding data
            if contract.symbol not in self.prices:
                self.prices[contract.symbol] = {'bid': float(ob_data['bidPrice']), 'ask': float(ob_data['askPrice'])}
            # else update the symbols data with the new or current bid/ask values
            else:
                self.prices[contract.symbol]['bid'] = float(ob_data['bidPrice'])
                self.prices[contract.symbol]['ask'] = float(ob_data['askPrice'])

            return self.prices[contract.symbol]

    def get_balances(self) -> typing.Dict[str, Balance]:
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        # key will be asset name value will be from the api documentation for accounts
        balances = dict()

        account_data = self._make_request("GET", "/fapi/v2/account", data)

        if account_data is not None:
            for a in account_data['assets']:
                balances[a['asset']] = Balance(a, "binance")

        return balances
    # price argument is not always needed and the same thing goes for tif (time in force) so we will assign hem to None
    #
    # Depending on current market conditions, Binance may send an "Order Does Not Exist" error message when requesting
    # an order status if the order status has not changed (not filled or cancelled) since you placed it.
    #
    # They do this to optimize their internal engine on days when the market fluctuates a lot. If the order status
    # changes though, the GET /fapi/v1/order will work anyway.
    def place_order(self, contract: Contract, side: str, quantity: float, order_type: str, price=None,
                    tif=None) -> OrderStatus:
        data = dict()
        data['symbol'] = contract.symbol
        data['side'] = side
        data['quantity'] = round(round(quantity / contract.lot_size) * contract.lot_size, 8)
        data['type'] = order_type

        if price is not None:
            data['price'] = round(round(price / contract.tick_size) * contract.tick_size, 8)

        if tif is not None:
            data['timeInForce'] = tif

        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("POST", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()

        data['orderId'] = order_id
        data['symbol'] = contract.symbol

        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("DELETE", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    def get_order_status(self, contract: Contract, order_id: int) -> OrderStatus:

        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['symbol'] = contract.symbol
        data['orderId'] = order_id
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("GET", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

    def _start_ws(self):
        self._ws = websocket.WebSocketApp(self._wss_url, on_open=self._on_open, on_close=self._on_close, on_error=self._on_error,
                                    on_message=self._on_message)
        while True:
            try:
                self._ws.run_forever()
            except Exception as e:
                logger.error("Binance error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Binance connection successfully opened")

        self.subscribe_channel(list(self.contracts.values()), "bookTicker")

    def _on_close(self, ws):
        logger.warning("Binance Websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error("Binance connection error: %s", msg)

    def _on_message(self, ws, msg: str):

        data = json.loads(msg)

        if "e" in data:
            if data['e'] == "bookTicker":
                # print("ok") --#1

                symbol = data['s']
                # print(symbol) --#2

                if symbol not in self.prices:
                    self.prices[symbol] = {'bid': float(data['b']), 'ask': float(data['a'])}
                    # print(symbol + " has been added to self.prices")  --#3
                    # else update with the current bid and ask prices
                else:
                    self.prices[symbol]['bid'] = float(data['b'])
                    self.prices[symbol]['ask'] = float(data['a'])
                    # print(symbol + " has been updated successfully")  --#4

                # print(symbol + " " + str(self.prices[symbol]['bid']) + " / " + str(self.prices[symbol]['ask']))  --#5
                # if symbol == "BTCUSDT":
                    # print("ok") --#7
                    # self._add_log(symbol + " " + str(self.prices[symbol]['bid']) + " / " +
                                  # str(self.prices[symbol]['ask']))  --#7

    def subscribe_channel(self, contracts: typing.List[Contract], channel: str):
        data = dict()
        data['method'] = "SUBSCRIBE"
        data['params'] = []

        for contract in contracts:
            data['params'].append(contract.symbol.lower() + "@" + channel)
        data['id'] = self._ws_id

        try:
            self._ws.send(json.dumps(data))
        except Exception as e:
            logger.error("Websocket error while subscribing to %s %s updates: %s", len(contracts), channel, e)

        self._ws_id += 1

    def get_all_openorders_status(self, contract: Contract) -> OrderStatus:

        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['symbol'] = contract.symbol
        data['signature'] = self._generate_signature(data)

        order_status = self._make_request("GET", "/fapi/v1/openOrders", data)

        if order_status is not None:
            order_status = OrderStatus(order_status, "binance")

        return order_status

