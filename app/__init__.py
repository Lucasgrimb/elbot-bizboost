from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from .utils.web_chat_utils import web_chat_blueprint  
from .utils.prospection_Epoint import prospection_blueprint 
from .views import send_template_blueprint  
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "https://bizboost.vercel.app"}})

    # Register the blueprints
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(web_chat_blueprint, url_prefix="/api/chat")
    app.register_blueprint(prospection_blueprint)
    app.register_blueprint(send_template_blueprint)

    return app