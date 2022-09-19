import datetime

import maya
import pytz
from flask import Flask, current_app, render_template
from bot.webapp.extensions import db, migrations, mail, caching, cors

from bot.webapp.blueprints.feed_importer import feed_importer as feed_importer_blueprint


def debug(message):
    """
    Print debug message to logger
    :param message:
    :return:
    """
    current_app.logger.debug(message)


def create_app(configuration=None) -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(configuration)

    db.init_app(app=app)
    migrations.init_app(app=app, db=db)
    mail.init_app(app=app)
    caching.init_app(app=app)
    cors.init_app(app=app)

    from bot.webapp import models
    app.app_context().push()

    @app.shell_context_processor
    def shell_context():
        return {
            'db': db,
            'app': app,
            'mail': mail
        }

    mail_settings = {
        "MAIL_SERVER": 'smtp.gmail.com',
        "MAIL_PORT": 465,
        "MAIL_USE_TLS": False,
        "MAIL_USE_SSL": True,
        "MAIL_USERNAME": "islati.sk@gmail.com",
        "MAIL_PASSWORD": "32buttcheeks!"
    }

    app.config.update(mail_settings)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.template_filter('slangtime')
    def slangtime(s):
        return maya.MayaDT.from_datetime(datetime.datetime.fromtimestamp(float(s), tz=pytz.utc)).slang_time()

    app.register_blueprint(feed_importer_blueprint)

    app.logger.info("Flask Application Created")

    return app
