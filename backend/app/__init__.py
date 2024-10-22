from flask import Flask
from flask_cors import CORS
from .routes.user_routes import user_bp
from .routes.product_routes import product_bp
from .routes.order_routes import order_bp

from flask_jwt_extended import JWTManager

# from flaskext.mysql import MySQL

from flasgger import Swagger

import configparser
import datetime

def create_app():
    app = Flask(__name__)

    # config_path = '/home/wangpython/Gogroupbuy/backend/config.ini'
    config_path = 'backend/config.ini'
    config = configparser.ConfigParser()
    config.read(config_path)

    app.config["JWT_SECRET_KEY"] = config['jwt']['JWT_SECRET_KEY']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)

    jwt = JWTManager(app)
    CORS(app)

    swagger_template = {"securityDefinitions": {"APIKeyHeader": {"type": "apiKey", "name": "Authorization", "in": "header"}}}
    Swagger(app, template=swagger_template)
    
    app.register_blueprint(user_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)

    return app