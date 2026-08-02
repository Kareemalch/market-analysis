from flask import Flask

from config import FLASK_SECRET_KEY
from routes.auth_api import bp as auth_api_bp
from routes.insights_api import bp as insights_api_bp
from routes.pages import bp as pages_bp
from routes.payments_api import bp as payments_api_bp
from routes.stock_api import bp as stock_api_bp
from routes.watchlist_api import bp as watchlist_api_bp

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

app.register_blueprint(pages_bp)
app.register_blueprint(auth_api_bp)
app.register_blueprint(stock_api_bp)
app.register_blueprint(watchlist_api_bp)
app.register_blueprint(payments_api_bp)
app.register_blueprint(insights_api_bp)

if __name__ == "__main__":
    app.run(debug=True)
