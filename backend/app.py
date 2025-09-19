from flask import Flask
from flask_cors import CORS
from api.routes import api_bp


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Enable CORS for frontend integration
    CORS(app)

    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='localhost', port=5000)