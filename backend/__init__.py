from flask import Flask
from .config import Config


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static"
    )
    app.config.from_object(Config)

    from .controllers.api import api_bp
    from .controllers.views import views_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    return app
