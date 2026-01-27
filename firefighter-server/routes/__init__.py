"""Blueprint registration for Flask routes.

This module centralizes all blueprint imports and provides a single
function to register them with the Flask application.
"""

from .health import health_bp
from .sessions import sessions_bp
from .export import export_bp
from .replay import replay_bp
from .search import search_bp
from .media import media_bp


def register_blueprints(app):
    """Register all blueprints with the Flask application."""
    app.register_blueprint(health_bp)
    app.register_blueprint(sessions_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    app.register_blueprint(replay_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(media_bp, url_prefix='/api')
