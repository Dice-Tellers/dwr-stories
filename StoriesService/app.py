import datetime

from flask import Flask

from StoriesService.database import db, Story
from StoriesService.urls import DEFAULT_DB
from StoriesService.views import blueprints


def create_app(database=DEFAULT_DB, wtf=False, login_disabled=False):
    flask_app = Flask(__name__)
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_SECRET_KEY'] = 'A SECRET KEY'
    flask_app.config['SECRET_KEY'] = 'ANOTHER ONE'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = database
    flask_app.config['WTF_CSRF_ENABLED'] = wtf
    flask_app.config['LOGIN_DISABLED'] = login_disabled

    for bp in blueprints:
        flask_app.register_blueprint(bp)
        bp.app = flask_app

    db.init_app(flask_app)
    db.create_all(app=flask_app)
    # with flask_app.app_context():
    #     q = db.session.query(Story).filter(Story.id == 1)
    #     story = q.first()
    #     if story is None:
    #         example = Story()
    #         example.text = 'Trial story of example admin user :)'
    #         example.figures = '#example#'
    #         example.author_id = 1
    #         example.is_draft = True
    #         print(example)
    #         db.session.add(example)
    #         db.session.commit()
    #     q = db.session.query(Story).filter(Story.id == 2)
    #     story = q.first()
    #     if story is None:
    #         example = Story()
    #         example.text = 'Trial story of example admin user :)'
    #         example.figures = '#story#'
    #         example.author_id = 2
    #         example.is_draft = False
    #         print(example)
    #         db.session.add(example)
    #         db.session.commit()
    #     q = db.session.query(Story).filter(Story.id == 3)
    #     story = q.first()
    #     if story is None:
    #         example = Story()
    #         example.text = 'Trial story of example admin user :)'
    #         example.figures = '#trial#'
    #         example.author_id = 3
    #         example.is_draft = False
    #         print(example)
    #         db.session.add(example)
    #         db.session.commit()
    #     q = db.session.query(Story).filter(Story.id == 4)
    #     story = q.first()
    #     if story is None:
    #         example = Story()
    #         example.text = 'Trial story of example admin user :)'
    #         example.figures = '#user#'
    #         example.author_id = 3
    #         example.is_draft = False
    #         example.date = datetime.datetime.strptime('2019-10-20', '%Y-%m-%d')
    #         print(example)
    #         db.session.add(example)
    #         db.session.commit()


    return flask_app


app = create_app()