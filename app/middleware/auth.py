import logging
import os
from functools import wraps

from dotenv import load_dotenv
from flask import current_app, jsonify, request

API_KEY_NAME = "X-API-KEY"
load_dotenv()


def get_api_tokens():
    """Retrieve accepted tokens from environment variables."""
    tokens_str = os.getenv("IMAGE_TOOLS_API_TOKENS", "")
    return [t.strip() for t in tokens_str.split(",") if t.strip()]


def get_test_token():
    """Get test token for testing mode."""
    return "Bearer test_token_for_testing_only"


def verify_token(f):
    """Decorator to check if the API key is valid."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If in testing mode, accept test token
        if current_app.config.get("TESTING", False):
            logging.warning("Testing mode enabled, accepting test token")
            api_key = request.headers.get(API_KEY_NAME)
            if api_key == get_test_token():
                return f(*args, **kwargs)

        api_key = request.headers.get(API_KEY_NAME)
        if not api_key:
            return (
                jsonify(
                    {
                        "error": "Authentication required",
                        "message": "Missing API Token in headers",
                        "success": False,
                    }
                ),
                401,
            )

        valid_tokens = get_api_tokens()
        if not valid_tokens:
            return (
                jsonify(
                    {
                        "error": "service unavailable",
                        "message": "Authentication service is not properly  initialized",
                        "success": False,
                    }
                ),
                500,
            )

        if api_key not in valid_tokens:
            return (
                jsonify(
                    {
                        "error": "invalid token",
                        "message": "The provided API token is invalid or has expired",
                        "success": False,
                    }
                ),
                401,
            )

        return f(*args, **kwargs)

    return decorated_function
