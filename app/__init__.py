from flask import Flask
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
from .utils.web_chat_utils import web_chat_blueprint  # Import the new blueprint

def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Register the blueprints for WhatsApp and Web Chat
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(web_chat_blueprint, url_prefix="/api/chat")

    return app
