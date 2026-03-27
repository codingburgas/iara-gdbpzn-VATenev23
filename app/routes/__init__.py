def register_blueprints(app):
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.incidents import incidents_bp
    from app.routes.firefighters import firefighters_bp
    from app.routes.equipment import equipment_bp
    from app.routes.communications import communications_bp  # <-- MUST BE HERE
    from app.routes.volunteers import volunteers_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.map import map_bp
    from app.routes.notifications import notifications_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(firefighters_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(communications_bp)  # <-- MUST BE REGISTERED
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(notifications_bp)