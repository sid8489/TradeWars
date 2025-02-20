import json
import logging

from flask_socketio import join_room, leave_room

import db
from extension import app, socketio  # Import from extensions
from routes import auth, groups, trading

app.register_blueprint(auth.bp)
app.register_blueprint(groups.bp)
app.register_blueprint(trading.bp)


def on_join(data):
    group_id = data['group_id']
    logging.info("Client asked to join group %s", group_id)
    """Handles the 'join_room' event from the client."""
    join_room(group_id)  # Join the room (using Flask-SocketIO's built-in function)
    socketio.emit('my_response', {'message': 'Successfully joined room ' + group_id})



def on_leave(data):
    """Handles the 'leave_room' event from the client."""
    group_id = data['group_id']
    logging.info("Client asked to leave group %s", group_id)
    leave_room(group_id)
    socketio.emit('my_response', {'message': 'Successfully left room ' + group_id})


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format="%(processName)s  %(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt='%d-%b-%y %H:%M:%S')
    db.init(json.loads(open("config/initData.json", "r").read()))
    socketio.on_event("join_group", on_join)
    socketio.on_event("leave_group", on_leave)
    logging.info(socketio.server.eio.handlers)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
