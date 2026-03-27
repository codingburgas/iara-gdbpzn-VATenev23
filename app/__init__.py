from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize extensions
bootstrap = Bootstrap()
db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    bootstrap.init_app(app)
    db.init_app(app)

    # Register template filters
    from app.utils import duration_filter
    app.template_filter('duration')(duration_filter)

    # Import and register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Create tables
    with app.app_context():
        db.create_all()
        print("Database tables created/updated!")

        # Create default templates
        from app.utils import create_default_templates
        create_default_templates()

    return app