#!/usr/bin/env python3
"""Firefighter Server - Socket.IO + REST API for sensor data collection.

Receives sensor data from Raspberry Pi via Socket.IO and stores in Qdrant.
Provides REST API for session management and data export.
"""

import os
import logging
from dotenv import load_dotenv

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

from lib.config import Config
from app_state import AppState
from routes import register_blueprints
from routes.socket_handlers import register_socket_handlers
from routes.sessions import init_socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
config = Config.from_env()
app.config["SECRET_KEY"] = config.server.secret_key

# Initialize shared state
AppState.init(config)

# Enable CORS for all origins including 'null' (file:// protocol)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
})

# Initialize Socket.IO
# Using threading mode for development stability
# For production with high concurrency, use gevent or eventlet
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# Register blueprints and socket handlers
register_blueprints(app)
register_socket_handlers(socketio)
init_socketio(socketio)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Firefighter Server")
    logger.info("=" * 60)
    logger.info(f"Host: {config.server.host}")
    logger.info(f"Port: {config.server.port}")
    logger.info(f"Debug: {config.server.debug}")
    logger.info(f"Qdrant: {config.qdrant.host}:{config.qdrant.port}")
    logger.info(f"PostgreSQL: {config.postgres.host}:{config.postgres.port}/{config.postgres.database}")
    logger.info("=" * 60)

    # Initialize vector store on startup
    AppState.get_vector_store()
    logger.info("[Qdrant] Sensor vector store initialized")

    # Initialize pose store on startup
    AppState.get_pose_store()
    logger.info("[Qdrant] Pose store initialized")

    # Initialize database
    AppState.get_database()
    AppState.get_session_repo()
    logger.info("[Database] PostgreSQL initialized")

    # Restore active session if server restarted
    repo = AppState.get_session_repo()
    active_session = repo.get_active()
    if active_session:
        AppState.current_session_id = active_session.id
        logger.info(f"[Session] Restored active session: {AppState.current_session_id}")

    socketio.run(
        app,
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
        allow_unsafe_werkzeug=True,  # Required for threading mode in development
    )
