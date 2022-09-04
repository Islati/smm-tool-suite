from flask import Flask
from webapp.extensions import db, migrations


def create_app(configuration=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(configuration)

    db.init_app(app=app)
    migrations.init_app(app=app, db=db)

    from webapp import models
    app.app_context().push()

    @app.shell_context_processor
    def shell_context():
        return {
            'db': db,
            'app': app
        }

    app.logger.info("Flask Application Created")

    return app
