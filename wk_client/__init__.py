from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from wk_client.config import Config

db = SQLAlchemy()
migrate = Migrate()
auth = HTTPBasicAuth()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from wk_client.routes import bp
    app.register_blueprint(bp)

    return app


from wk_client import models

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': models.User, 'CashFlow': models.CashFlow, 'Loan': models.Loan, 'Decision': models.Decision}