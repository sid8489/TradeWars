import logging
import threading

from flasgger import Swagger, swag_from
from flask import Blueprint, request, jsonify, Flask
from extension import app, socketio  # Import from extensions
from db import db_instance


bp = Blueprint('trading', __name__, url_prefix='')
db = db_instance

@bp.route('/begin_session/<group_id>', methods=['POST'])
@swag_from({
    'parameters': [
        {
            'name': 'group_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'ID of the trading group'
        }
    ],
    'responses': {
        200: {'description': 'Session started'},
        400: {'description': 'Session already running or finished'},
        404: {'description': 'Group not found'}
    }
})
def begin_session(group_id):
    group_state = db.get_group_state(group_id)
    if not group_state:
        return jsonify({"error": "Group not found"}), 404

    if group_state == "STARTED":
        return jsonify({"error": "Session already running for this group"}), 400
    if group_state == "FINISHED":
        return jsonify({"error": "Session already finished for this group"}), 400

    thread = threading.Thread(target=market_feed_loop, args=(group_id, db.get_group_duration(group_id)))
    db.being_session(group_id)
    thread.start()
    return jsonify({"message": "Session started"}), 200

def market_feed_loop(group_id, duration):
    try:
        for _ in range(duration):
            try:
                market_data = db.simulate(group_id)
                logging.info(f"Market Data: {market_data}", )
                socketio.emit('market_update', market_data, room=group_id)  # Use socketio.emit
            except Exception as e:
                logging.error("Exception while market update", exc_info=e)
            socketio.sleep(1)  # Use socketio.sleep to avoid blocking
    finally:
        db.end_session(group_id)

@bp.route('/get_stock_list/<group_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {
            'name': 'group_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'ID of the trading group'
        }
    ],
    'responses': {
        200: {'description': 'List of stocks'},
        404: {'description': 'Group not found'}
    }
})
def get_stock_list(group_id):
    stocks = db.get_stocks(group_id)
    if not stocks:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(stocks), 200

@bp.route('/get_user_positions/<user_id>/<group_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User ID'},
        {'name': 'group_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Trading group ID'}
    ],
    'responses': {
        200: {'description': 'User positions'},
        404: {'description': 'User or group not found'}
    }
})
def get_user_positions_route(user_id, group_id):
    positions = db.get_user_positions(group_id, user_id)
    if not positions:
        return jsonify({"error": "User or group not found"}), 404
    return jsonify(positions), 200

@bp.route('/place_order', methods=['POST'])
@swag_from({
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'user_id': {'type': 'string'},
                'group_id': {'type': 'string'},
                'stock': {'type': 'string'},
                'quantity': {'type': 'integer'},
                'direction': {'type': 'string', 'enum': ['BUY', 'SELL']}
            }
        }}
    ],
    'responses': {
        200: {'description': 'Order placed successfully'},
        400: {'description': 'Invalid request parameters'},
        404: {'description': 'Stock or group not found'}
    }
})
def place_order():
    data = request.get_json()
    user_id = data.get('user_id')
    group_id = data.get('group_id')
    stock = data.get('stock')
    quantity = data.get('quantity')
    direction = data.get('direction')

    group_state = db.get_group_state(group_id)
    if not group_state:
        return jsonify({"error": "Group not found"}), 404

    if group_state != "STARTED":
        return jsonify({"error": "Session is not active"}), 400

    if quantity <= 0:
        return jsonify({"error": "Quantity must be positive"}), 400
    if direction not in ['BUY', 'SELL']:
        return jsonify({"error": "Direction must be either BUY or SELL"}), 400
    price = db.get_stock_prices(group_id, stock)
    if price is None:
        return jsonify({"error": "Stock not found"}), 404

    if direction == 'SELL':
        positions = db.get_user_positions(group_id, user_id)
        open_position = None
        for oP in positions["open_positions"]:
            if oP.stock == stock:
                open_position = oP
        if open_position is None or open_position.quantity < quantity:
            return jsonify({"error": "Insufficient stock to sell"}), 400
    elif direction == 'BUY':
        cost = price * quantity
        if db.get_user_available_coins(group_id, user_id) < cost:
            return jsonify({"error": "Insufficient margin"}), 400

    db.execute_trade(user_id, stock, quantity, price, direction, group_id)
    return jsonify({"message": "Order Placed successfully"}), 200

@bp.route('/get_price_series/<group_id>/<stock_symbol>/<freq>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'group_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Trading group ID'},
        {'name': 'stock_symbol', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Stock symbol'},
        {'name': 'freq', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Price series frequency'}
    ],
    'responses': {
        200: {'description': 'Stock price series'},
        404: {'description': 'Stock or group not found'}
    }
})
def get_current_price(group_id, stock_symbol, freq):
    group_state = db.get_group_state(group_id)
    if not group_state:
        return jsonify({"error": "Group not found"}), 404

    if group_state == "CREATED":
        return jsonify({"error": "Session is not started"}), 400

    price = db.get_stock_price_series(group_id, stock_symbol, freq)
    ohlc_json = price.reset_index()
    ohlc_json["timestamp"] = ohlc_json["index"].astype("int64") // 1_000_000_000
    ohlc_json = ohlc_json.drop(columns=["index"])
    return jsonify({"price": ohlc_json.to_dict(orient="records")}), 200

