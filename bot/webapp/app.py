from bot.webapp import create_app
from bot.webapp.config import Config

app = create_app(Config())
