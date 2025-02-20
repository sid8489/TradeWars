from flask import Flask
from flask_socketio import SocketIO
from flasgger import Swagger

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins for local dev

app.config['SWAGGER'] = {
    'title': 'Trading API',
    'uiversion': 3,
    'specs_route': '/apidocs/'
}
swagger = Swagger(app)