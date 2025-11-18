from flask import Flask

from backend.config import Config
from backend.controllers.api import api_bp
from backend.controllers.views import views_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config.from_object(Config)

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    return app
