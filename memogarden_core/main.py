"""Flask application entry point."""

import logging
from flask import Flask, jsonify
from flask_cors import CORS

from .config import settings
from .db import init_db
from .exceptions import ResourceNotFound, ValidationError, MemoGardenError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create Flask app
app = Flask(__name__)

# CORS configuration
CORS(app, origins=settings.cors_origins, supports_credentials=True)


# Database initialization (runs once on app startup)
def initialize_database():
    """Initialize database on app startup."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# Initialize database with app context
with app.app_context():
    initialize_database()


# Error handlers
@app.errorhandler(ResourceNotFound)
def handle_not_found(error):
    """Handle ResourceNotFound exceptions."""
    response = {
        "error": {
            "type": "ResourceNotFound",
            "message": error.message
        }
    }
    if error.details:
        response["error"]["details"] = error.details
    return jsonify(response), 404


@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle ValidationError exceptions."""
    response = {
        "error": {
            "type": "ValidationError",
            "message": error.message
        }
    }
    if error.details:
        response["error"]["details"] = error.details
    return jsonify(response), 400


@app.errorhandler(MemoGardenError)
def handle_memo_garden_error(error):
    """Handle generic MemoGardenError exceptions."""
    response = {
        "error": {
            "type": error.__class__.__name__,
            "message": error.message
        }
    }
    if error.details:
        response["error"]["details"] = error.details
    return jsonify(response), 500


@app.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({
        "error": {
            "type": "InternalServerError",
            "message": "An internal error occurred"
        }
    }), 500


# Health check endpoint
@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


# Register API blueprints
from .api.v1.transactions import transactions_bp

app.register_blueprint(
    transactions_bp,
    url_prefix=f"{settings.api_v1_prefix}/transactions"
)


if __name__ == "__main__":
    app.run(debug=True)
