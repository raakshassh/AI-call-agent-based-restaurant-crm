from flask import Flask
from app.routes import configure_routes

app = Flask(__name__)

# Configure routes (including Gemini AI processing)
configure_routes(app)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
