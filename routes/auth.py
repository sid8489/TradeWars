from flask import Blueprint, request, jsonify
import uuid
from db import users, groups, db_instance
from models import UserDataPerSession
from flasgger import swag_from

bp = Blueprint('auth', __name__, url_prefix='/')

@bp.route('/register', methods=['POST'])
@swag_from({
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'phone': {'type': 'string'},
                'name': {'type': 'string'},
                'password': {'type': 'string'}
            }
        }}
    ],
    'responses': {
        201: {'description': 'User registered successfully'},
        400: {'description': 'Missing fields or user already exists'}
    }
})
def register():
    data = request.get_json()
    phone = data.get('phone')
    name = data.get('name')
    password = data.get('password')

    if not all([phone, name, password]):
        return jsonify({"error": "Missing fields"}), 400

    with db_instance.lock:
        if any(user.phone == phone for user in users.values()):
            return jsonify({"error": "User with this phone number already exists"}), 400

        user_id = f"UI{int(uuid.uuid4().hex[:12], 16) % 10**10}"
        db_instance.add_user(user_id, phone, name, password)

    return jsonify({"user_id": user_id}), 201

@bp.route('/login', methods=['POST'])
@swag_from({
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'phone': {'type': 'string'},
                'password': {'type': 'string'}
            }
        }}
    ],
    'responses': {
        200: {'description': 'Login successful'},
        401: {'description': 'Invalid credentials'}
    }
})
def login():
    data = request.get_json()
    phone = data.get('phone')
    password = data.get('password')

    with db_instance.lock:
        for user_id, user in users.items():
            if user.phone == phone and user.password == password:
                return jsonify({"user_id": user_id}), 200

    return jsonify({"error": "Invalid credentials"}), 401

@bp.route('/getUserByUserId/<user_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User ID'}
    ],
    'responses': {
        200: {'description': 'User details'},
        404: {'description': 'User not found'}
    }
})
def get_user_details(user_id):
    with db_instance.lock:
        user = users.get(user_id)
        if user:
            return jsonify({
                "user_id": user_id,
                "phone": user.phone,
                "name": user.name
            }), 200

    return jsonify({"error": "User not found"}), 404

@bp.route('/getUserByPhoneNumber/<phone>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'phone', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User phone number'}
    ],
    'responses': {
        200: {'description': 'User details'},
        404: {'description': 'User not found'}
    }
})
def get_user_by_phone(phone):
    with db_instance.lock:
        for user_id, user in users.items():
            if user.phone == phone:
                return jsonify({
                    "user_id": user_id,
                    "phone": user.phone,
                    "name": user.name
                }), 200

    return jsonify({"error": "User not found"}), 404