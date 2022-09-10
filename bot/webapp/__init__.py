from flask import Flask, current_app, render_template
from bot.webapp.extensions import db, migrations, mail


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

    from bot.webapp import models
    app.app_context().push()

    @app.shell_context_processor
    def shell_context():
        return {
            'db': db,
            'app': app,
            'mail': mail
        }

    @app.route('/')
    def index():
        return render_template('index.html')

    app.logger.info("Flask Application Created")

    return app
