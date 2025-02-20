import random
from typing import List, Dict
from datetime import datetime
import pandas as pd

from utils import generate_stock_time_series


class User:
    def __init__(self, phone, name, password):
        self.phone = phone
        self.name = name
        self.password = password

    def __repr__(self):  # For easier debugging/printing
        return f"User(phone='{self.phone}', name='{self.name}')"



class Group:
    def __init__(self, group_id, name, creator_id, stock_list, per_user_coins, duration):
        self.group_id = group_id
        self.name = name
        self.creator_id = creator_id
        self.stocks = {}
        for stock in stock_list:
            self.stocks[stock] = StockData(stock)
        self.per_user_coins = per_user_coins
        self.duration = duration
        self.user_data: Dict[str, UserDataPerSession] = {}
        self.state = "CREATED"
        self.started_at = None
        self.ended_at = None
        self.active_duration = 0
        for stock in self.stocks.values():
            initial_price = random.uniform(100, 200)
            stock.prices_per_second = generate_stock_time_series(initial_price, duration)

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "name": self.name,
            "creator_id": self.creator_id,
            "stocks": [k for k, v in self.stocks.items()],
            "per_user_coins": self.per_user_coins,
            "duration": self.duration,
            "user_data": {user_id: user_data.to_dict() for user_id, user_data in self.user_data.items()},
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "active_duration": self.active_duration,
        }

    def to_ohlc_candles(self, stock_id, freq):
        stock_ = self.stocks[stock_id]

        # Create a pandas Series with the price data and a datetime index
        price_series = pd.Series(
            stock_.prices_per_second[:self.active_duration+1],
            index=pd.to_datetime(self.started_at, unit='s') + pd.to_timedelta(pd.Series(range(self.active_duration + 1)), unit='s')
        )
        # Resample the data to the desired frequency and get OHLC values
        ohlc_df = price_series.resample(freq).ohlc()
        return ohlc_df
class StockData:
    def __init__(self, id):
        self.id = id
        self.prices_per_second = []

class UserDataPerSession:
    def __init__(self, coins):
        self.available_coins = coins
        self.mtm = 0.0
        self.trades: List[Trade] = []
        self.open_positions: List[OpenPosition] = []
        self.roundtrips: List[RoundTrip] = []

    def update_mtm(self):
        mtm = 0.0
        for rt in self.roundtrips:
            mtm += rt.pnl
        for op in self.open_positions:
            mtm += op.pnl
        self.mtm = mtm

    def to_dict(self):
        return {
            "available_coins": self.available_coins,
            "mtm": self.mtm,
            "trades": [trade.to_dict() for trade in self.trades],
            "open_positions": [position.to_dict() for position in self.open_positions],
            "roundtrips": [round_trip.to_dict() for round_trip in self.roundtrips],
        }

class RoundTrip:
    def __init__(self, user_id, stock, quantity, entry_price, entry_time, exit_price, exit_time, direction):
        self.user_id = user_id
        self.stock = stock
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.direction = direction
        self.pnl = ((exit_price - entry_price) * quantity) * (1 if direction == "BUY" else -1)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "stock": self.stock,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat(),
            "direction": self.direction,
            "pnl": self.pnl,
        }

    def __repr__(self):
        return f"RoundTrip(user_id='{self.user_id}', stock='{self.stock}', quantity={self.quantity}, entry_price={self.entry_price}, entry_time={self.entry_time}, exit_price={self.exit_price}, exit_time={self.exit_time}, direction='{self.direction}')"

class OpenPosition:
    def __init__(self, user_id, stock, quantity, entry_price, entry_time, direction):
        self.user_id = user_id
        self.stock = stock
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction
        self.current_price = entry_price
        self.pnl = 0.0

    def update_pnl(self):
        self.pnl = ((self.current_price - self.entry_price) * self.quantity) * (1 if self.direction == "BUY" else -1)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "stock": self.stock,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "direction": self.direction,
            "current_price": self.current_price,
            "pnl": self.pnl,
        }

    def __repr__(self):
        return f"OpenPosition(user_id='{self.user_id}', stock='{self.stock}', quantity={self.quantity}, entry_price={self.entry_price}, entry_time={self.entry_time}, direction='{self.direction}')"

class Trade:
    def __init__(self, user_id, stock, quantity, price, direction):
        self.user_id = user_id
        self.stock = stock
        self.quantity = quantity
        self.price = price
        self.direction = direction  # "BUY" or "SELL"
        self.timestamp = datetime.now()  # Add timestamp to the trade

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "stock": self.stock,
            "quantity": self.quantity,
            "price": self.price,
            "direction": self.direction,
            "timestamp": self.timestamp.isoformat(),
        }


    def __repr__(self):
        return f"Trade(user_id='{self.user_id}', stock='{self.stock}', quantity={self.quantity}, price={self.price}, direction='{self.direction}', timestamp={self.timestamp})"