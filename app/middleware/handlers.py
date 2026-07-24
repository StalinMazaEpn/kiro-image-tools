import logging
import os

from dotenv import load_dotenv
from flask import jsonify, request

load_dotenv()
debug = os.getenv("AUTOMATION_API_DEBUG", "False").lower() == "true"


def register_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(e):
        if debug:
            logging.error(f"Bad request: {request.url}")
        return (
            jsonify({"error": "Bad Request", "message": str(e), "success": False}),
            400,
        )

    @app.errorhandler(404)
    def not_found(e):
        if debug:
            logging.error(f"Resource not found: {request.url}")
        return jsonify({"error": "Resource not found", "success": False}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        if debug:
            logging.error(f"Method not allowed: {request.method} {request.url}")
        return (
            jsonify(
                {
                    "error": "Method Not Allowed",
                    "message": str(e),
                    "success": False,
                }
            ),
            405,
        )


def register_request_hooks(app):

    @app.before_request
    def log_request_info():
        if debug:
            print("Headers:", request.headers)
            print("Body:", request.get_data())
