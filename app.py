import json
import logging

import flask
from flask_socketio import join_room, leave_room
import db
from extension import app, socketio  # Import from extensions
from routes import auth, groups, trading

logging.basicConfig(level=logging.INFO,
                    format="%(processName)s  %(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt='%d-%b-%y %H:%M:%S')

# Initialize DB at import time
with open("./config/initData.json", "r") as f:
    db.init(json.load(f))

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(groups.bp)
app.register_blueprint(trading.bp)



def get_all_client_sessions():
    """Returns a list of all active client session IDs."""
    return list(socketio.server.manager.rooms.get('/', {}).keys())

def on_join(data):
    group_id = data['group_id']
    user_id = data['user_id']
    session_id = flask.request.sid
    trading.rooms[session_id] = {'room_id': group_id+user_id, "user_id": user_id}
    logging.info("Client asked to join group %s", group_id)
    join_room(group_id+user_id)
    socketio.emit('my_response', {'message': 'Successfully joined room ' + group_id})

def on_join_group_details(data):
    group_id = data['group_id']
    freq = data['freq']
    user_id = data['user_id']
    session_id = flask.request.sid
    trading.details_rooms[session_id] = {'freq': freq, 'room_id': group_id+"details"+freq+user_id, "user_id": user_id}
    logging.info("Client asked to join group details %s", group_id)
    join_room(group_id+"details"+freq+user_id)
    socketio.emit('my_response', {'message': 'Successfully joined room ' + group_id})

def on_join_group_leaderboard(data):
    group_id = data['group_id']
    logging.info("Client asked to join group Leaderboard %s", group_id)
    join_room(group_id+"leaderboard")
    socketio.emit('my_response', {'message': 'Successfully joined room ' + group_id})

def on_leave(data):
    group_id = data['group_id']
    logging.info("Client asked to leave group %s", group_id)
    leave_room(group_id)
    socketio.emit('my_response', {'message': 'Successfully left room ' + group_id})


# Attach event handlers
socketio.on_event("join_group", on_join)
socketio.on_event("join_group_details", on_join_group_details)
socketio.on_event("join_group_leaderboard", on_join_group_leaderboard)
socketio.on_event("leave_group", on_leave)


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True)
