import threading
from datetime import datetime
from typing import Dict, List

from models import User, Group, Trade, OpenPosition, RoundTrip, UserDataPerSession


class InMemoryDB:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._groups: Dict[str, Group] = {}
        self.lock = threading.RLock()

    def add_user(self, user_id: str, phone: str, name: str, password: str):
        with self.lock:
            self._users[user_id] = User(phone, name, password)

    def get_user(self, phone: str):
        return self._users.get(phone)

    def add_group(self, group_id: str, name: str, creator_id: str, stock_list, per_user_coins, duration):
        with self.lock:
            if creator_id not in self._users:
                raise ValueError("Creator must be a registered user")
            group = Group(group_id, name, creator_id, stock_list, per_user_coins, duration)
            self._groups[group_id] = group
            return group

    def get_group(self, group_id: str):
        return self._groups.get(group_id)

    def get_group_state(self, group_id: str) -> str:
        with self.lock:
            if group_id not in self._groups:
                return None
            return self._groups[group_id].state

    def get_group_duration(self, group_id: str) -> str:
        with self.lock:
            return self._groups[group_id].duration

    def being_session(self, group_id: str) -> str:
        with self.lock:
            self._groups[group_id].state = "STARTED"
            self._groups[group_id].started_at = int(datetime.now().timestamp())

    def end_session(self, group_id: str) -> str:
        with self.lock:
            self._groups[group_id].state = "FINISHED"
            self._groups[group_id].ended_at = int(datetime.now().timestamp())

    def simulate(self, group_id: str) -> Dict[str, float]:
        with self.lock:
            prices = {}
            for stock in self._groups[group_id].stocks.values():
                prices[stock.id] = stock.prices_per_second[self._groups[group_id].active_duration]

            self._groups[group_id].active_duration += 1
            self._update_pnl(self._groups[group_id])
            return prices

    def get_stock_prices(self, group_id: str, stock_id: str) -> float:
        with self.lock:
            if stock_id not in self._groups[group_id].stocks:
                return None
            return self._groups[group_id].stocks[stock_id].prices_per_second[self._groups[group_id].active_duration]

    def get_stock_price_series(self, group_id: str, stock_id: str, freq: str) -> Dict:
        with self.lock:
            price = self._groups[group_id].to_ohlc_candles(stock_id, freq)
            ohlc_json = price.reset_index()
            ohlc_json["timestamp"] = ohlc_json["index"].astype("int64") // 1_000_000_000
            ohlc_json = ohlc_json.drop(columns=["index"])
            return ohlc_json.to_dict(orient="records")

    def get_stocks(self, group_id: str) -> List[str]:
        with self.lock:
            if group_id not in self._groups:
                return None
            return [k for k, v in self._groups[group_id].stocks.items()]

    def get_user_positions(self, group_id: str, user_id: str):
        with self.lock:
            if group_id not in self._groups:
                return None
            group = self._groups[group_id]
            if user_id not in group.user_data:
                return None
            user = group.user_data[user_id]
            return {
                "open_positions": user.open_positions,
                "closed_positions": user.roundtrips,
            }

    def get_leaderboard(self, group_id: str):
        with self.lock:
            leaderboard = []
            for user_id, user_data in groups[group_id].user_data.items():
                leaderboard.append({"user_id": user_id, "user_name": users[user_id].name , "mtm": user_data.mtm})
            sorted_leaderboard = sorted(leaderboard, key=lambda item: item["mtm"], reverse=True)
            return sorted_leaderboard

    def get_user_available_coins(self, group_id: str, user_id: str):
        with self.lock:
            user = self._groups[group_id].user_data[user_id]
            return user.available_coins

    def execute_trade(self, user_id: str, stock: str, quantity: int, price: float, direction: str, group_id: str):
        with self.lock:
            group = self._groups[group_id]
            trade = Trade(user_id, stock, quantity, price, direction)
            group.user_data[user_id].trades.append(trade)
            self._handle_position(group, user_id, trade)
            self._handle_coins(group, user_id, trade)

    def _handle_position(self, group: Group, user_id: str, trade: Trade):
        user_data = group.user_data[user_id]
        if trade.direction == "BUY":
            existing_position = next((pos for pos in user_data.open_positions if pos.stock == trade.stock), None)
            if existing_position:
                existing_position.quantity += trade.quantity
                existing_position.entry_price = ((existing_position.entry_price * existing_position.quantity) + (trade.price * trade.quantity)) / (existing_position.quantity + trade.quantity)
            else:
                position = OpenPosition(user_id, trade.stock, trade.quantity, trade.price, trade.timestamp, "BUY")
                user_data.open_positions.append(position)
        elif trade.direction == "SELL":
            for position in user_data.open_positions:
                if position.stock == trade.stock:
                    round_trip = RoundTrip(
                        user_id, trade.stock, trade.quantity, position.entry_price, position.entry_time,
                        trade.price, trade.timestamp, position.direction
                    )
                    user_data.roundtrips.append(round_trip)
                    if position.quantity > trade.quantity:
                        position.quantity -= trade.quantity
                    else:
                        user_data.open_positions.remove(position)
                    break  # Assume we match only one position per trade

    def _handle_coins(self, group: Group, user_id: str, trade: Trade):
        if trade.direction == "BUY":
            group.user_data[user_id].available_coins -= trade.price * trade.quantity
        else:
            group.user_data[user_id].available_coins += trade.price * trade.quantity

    def _update_pnl(self, group: Group):
        for user in group.user_data.values():
            for op in user.open_positions:
                op.current_price = group.stocks[op.stock].prices_per_second[group.active_duration]
                op.update_pnl()
            user.update_mtm()

    def get_pnl(self, group_id: str, user_id: str):
        with self.lock:
            data = {  }
            for stock in self._groups[group_id].stocks.keys():
                data[stock] = {
                    "holdings": 0,
                    "unrealized_pnl": 0,
                    "realized_pnl": 0,
                }
            user = self._groups[group_id].user_data[user_id]
            for op in user.open_positions:
                data[op.stock]["holdings"] = op.quantity
                data[op.stock]["unrealized_pnl"] = op.pnl
                data[op.stock]["op"] = op.to_dict()
            for rt in user.roundtrips:
                data[rt.stock]["realized_pnl"] += rt.pnl
            return data

    def get_margin(self, group_id: str, user_id: str):
        with self.lock:
            data = {  }
            data["available_coins"] = self._groups[group_id].user_data[user_id].available_coins
            return data

    def join_group(self, group_id: str, user_id: str):
        with self.lock:
            self._groups[group_id].user_data[user_id] = UserDataPerSession(self._groups[group_id].per_user_coins)

    def check_user(self, group_id: str, user_id: str):
        with self.lock:
            return user_id in self._groups[group_id].user_data

db_instance = InMemoryDB()
users = db_instance._users
groups = db_instance._groups


def init(data):
    for user in data["users"]:
        db_instance.add_user(user["id"], user["phone"], user["name"], user["password"])
    for group in data["groups"]:
        db_instance.add_group(group["id"], group["name"], group["creator_id"], group["stock_list"], group["per_user_coins"], group["duration"])
        groups.get(group["id"]).user_data[group["creator_id"]] = UserDataPerSession(group["per_user_coins"])
        for user_id in group["joinies"]:
            groups.get(group["id"]).user_data[user_id] = UserDataPerSession(group["per_user_coins"])