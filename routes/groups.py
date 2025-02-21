from flask import Blueprint, request, jsonify
import uuid
from db import users, groups, db_instance
from models import UserDataPerSession
from flasgger import swag_from

bp = Blueprint('groups', __name__, url_prefix='/')

@bp.route('/createGroup', methods=['POST'])
@swag_from({
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'creator_id': {'type': 'string'},
                'stock_list': {'type': 'array', 'items': {'type': 'string'}},
                'per_user_coins': {'type': 'integer'},
                'duration': {'type': 'integer'}
            }
        }}
    ],
    'responses': {
        201: {'description': 'Group created successfully'},
        400: {'description': 'Missing fields'},
        404: {'description': 'User not found'}
    }
})
def create_group():
    data = request.get_json()
    name = data.get('name')
    creator_id = data.get('creator_id')
    stock_list = data.get("stock_list")
    per_user_coins = data.get("per_user_coins")
    duration = data.get("duration")

    if not all([creator_id, stock_list, per_user_coins, duration]):
        return jsonify({"error": "Missing fields"}), 400

    if creator_id not in users:
        return jsonify({"error": "User not found"}), 404

    group_id = f"GI{int(uuid.uuid4().hex[:12], 16) % 10**10}"
    db_instance.add_group(group_id, name, creator_id, stock_list, per_user_coins, duration)
    groups.get(group_id).user_data[creator_id] = UserDataPerSession(per_user_coins)
    return jsonify({"group_id": group_id}), 201

@bp.route('/joinGroup', methods=['POST'])
@swag_from({
    'parameters': [
        {'name': 'body', 'in': 'body', 'required': True, 'schema': {
            'type': 'object',
            'properties': {
                'user_id': {'type': 'string'},
                'group_id': {'type': 'string'}
            }
        }}
    ],
    'responses': {
        200: {'description': 'Joined group successfully'},
        400: {'description': 'Missing fields'},
        404: {'description': 'User or group not found'}
    }
})
def join_group():
    data = request.get_json()
    user_id = data.get('user_id')
    group_id = data.get('group_id')

    if not all([user_id, group_id]):
       return jsonify({"error": "Missing fields"}), 400

    if user_id not in users:
        return jsonify({"error": "User not found"}), 404

    if group_id not in groups:
        return jsonify({"error": "Group not found"}), 404

    if group_id in groups.get(group_id).user_data.keys():
        return jsonify({"error": "User already joined"}), 200

    groups.get(group_id).user_data[user_id] = UserDataPerSession(groups.get(group_id).per_user_coins)
    return jsonify({"message": "Joined group successfully"}), 200

@bp.route('/getGroups/<user_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User ID'}
    ],
    'responses': {
        200: {'description': 'List of groups the user belongs to'},
        404: {'description': 'User not found'}
    }
})
def get_groups(user_id):
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404

    user_groups = []
    for group_id, group_data in groups.items():
        if user_id in group_data.user_data:
            user_groups.append(group_data.to_dict())
    return jsonify(user_groups), 200

@bp.route('/getGroupDetails/<group_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'group_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Group ID'}
    ],
    'responses': {
        200: {'description': 'Group details'},
        404: {'description': 'Group not found'}
    }
})
def get_group_details(group_id):
    if group_id not in groups:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(groups[group_id].to_dict()), 200

@bp.route('/getLeaderboard/<group_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'group_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Group ID'}
    ],
    'responses': {
        200: {'description': 'Leaderboard data'},
        404: {'description': 'Group not found'}
    }
})
def get_leaderboard(group_id):
    if group_id not in groups:
        return jsonify({"error": "Group not found"}), 404

    leaderboard = []
    for user_id, user_data in groups[group_id].user_data.items():
        leaderboard.append({"user_id": user_id, "user_name": users[user_id].name , "mtm": user_data.mtm})

    sorted_leaderboard = sorted(leaderboard, key=lambda item: item["mtm"], reverse=True)

    return jsonify(sorted_leaderboard), 200

@bp.route('/getAllGroups', methods=['GET'])
@swag_from({
    'parameters': [
    ],
    'responses': {
        200: {'description': 'List of groups'},
        404: {'description': 'User not found'}
    }
})
def get_all_groups():
   data = []
   for group_id, group_data in groups.items():
        data.append(group_data.to_dict())
   return jsonify(data), 200

@bp.route('/getAllJoinableGroupsForUser/<user_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User ID'}
    ],
    'responses': {
        200: {'description': 'List of joinable groups for given user'},
        404: {'description': 'User not found'}
    }
})
def get_all_joinable_groups_for_user(user_id):
   data = []
   for group_id, group_data in groups.items():
       if user_id not in group_data.user_data.keys():
           if group_data.state == 'FINISHED':
               continue
           data.append(group_data.to_dict())
   return jsonify(data), 200


@bp.route('/getMargin/<group_id>/<user_id>', methods=['GET'])
@swag_from({
    'parameters': [
        {'name': 'group_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'Group ID'},
        {'name': 'user_id', 'in': 'path', 'type': 'string', 'required': True, 'description': 'User ID'}
    ],
    'responses': {
        200: {'description': 'Available Margin'},
        404: {'description': 'User not found'}
    }
})
def get_margin(group_id, user_id):
    if group_id not in groups:
        return jsonify({"error": "Group not found"}), 404
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    return jsonify(db_instance.get_margin(group_id, user_id)), 200