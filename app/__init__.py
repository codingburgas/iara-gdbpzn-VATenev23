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
        _ensure_columns()
        print("Database tables created/updated!")

        # Create default templates
        from app.utils import create_default_templates
        create_default_templates()

    return app


def _ensure_columns():
    """Lightweight SQLite migration: add new columns to existing tables
    without dropping data. Runs ALTER TABLE ADD COLUMN for any column the
    model defines but the database is missing."""
    from sqlalchemy import inspect, text

    wanted = {
        'vehicle': {
            'route_polyline': 'TEXT',
            'route_started_at': 'DATETIME',
            'route_total_seconds': 'FLOAT',
            'route_real_seconds': 'FLOAT',
            'route_distance_m': 'FLOAT',
            'route_dest_lat': 'FLOAT',
            'route_dest_lng': 'FLOAT',
        },
        'incident': {
            'is_major': 'BOOLEAN DEFAULT 0',
            'parent_incident_id': 'INTEGER',
        },
    }

    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    for table, columns in wanted.items():
        if table not in existing_tables:
            continue
        present = {col['name'] for col in inspector.get_columns(table)}
        for name, col_type in columns.items():
            if name not in present:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {col_type}'))
                print(f"  + added column {table}.{name}")
        db.session.commit()