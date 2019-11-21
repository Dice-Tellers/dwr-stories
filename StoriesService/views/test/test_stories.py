import datetime
import json

import flask_testing
from flask import jsonify

from StoriesService.app import create_app
from StoriesService.database import db, Story
from StoriesService.urls import *


class TestStories(flask_testing.TestCase):
    app = None

    # First thing called
    def create_app(self):
        global app
        app = create_app(database=TEST_DB)
        return app

    # Set up database for testing here
    def setUp(self) -> None:
        with app.app_context():
            # Create the first story, default from teacher's code
            example = Story()
            example.text = 'Trial story of example admin user :)'
            example.author_id = 1
            example.figures = '#example#admin#'
            example.is_draft = False
            example.date = datetime.datetime.strptime('2019-10-20', '%Y-%m-%d')
            db.session.add(example)
            db.session.commit()

            # Create a story that shouldn't be seen in /latest
            example = Story()
            example.text = 'Old story (dont see this in /latest)'
            example.date = datetime.datetime.strptime('2019-10-10', '%Y-%m-%d')
            example.author_id = 2
            example.is_draft = False
            example.figures = '#example#abc#'
            db.session.add(example)
            db.session.commit()

            # Create a story that should be seen in /latest
            example = Story()
            example.text = 'You should see this one in /latest'
            example.date = datetime.datetime.strptime('2019-10-13', '%Y-%m-%d')
            example.author_id = 2
            example.is_draft = False
            example.figures = '#example#abc#'
            db.session.add(example)
            db.session.commit()

            # Random draft from a non-admin user
            example = Story()
            example.text = 'DRAFT from not admin'
            example.date = datetime.datetime.strptime('2018-12-30', '%Y-%m-%d')
            example.author_id = 3
            example.is_draft = True
            example.figures = '#example#nini#'
            db.session.add(example)
            db.session.commit()

            # Create a very old story for range searches purpose
            example = Story()
            example.text = 'very old story (11 11 2011)'
            example.date = datetime.datetime.strptime('2011-11-11', '%Y-%m-%d')
            example.author_id = 3
            example.is_draft = False
            example.figures = '#example#nini#'
            example.date = datetime.datetime(2011, 11, 11)
            db.session.add(example)
            db.session.commit()

    # Executed at end of each test
    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()

    def test_all_stories(self):
        response = self.client.get('/stories')
        body = json.loads(str(response.data, 'utf8'))
        self.assertEqual(body, [
            {'author_id': 1, 'date': 'Sun, 20 Oct 2019 00:00:00 GMT', 'figures': '#example#admin#', 'id': 1,
             'is_draft': False, 'text': 'Trial story of example admin user :)'},
            {'author_id': 2, 'date': 'Sun, 13 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 3,
             'is_draft': False, 'text': 'You should see this one in /latest'},
            {'author_id': 2, 'date': 'Thu, 10 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 2,
             'is_draft': False, 'text': 'Old story (dont see this in /latest)'},
            {'author_id': 3, 'date': 'Fri, 11 Nov 2011 00:00:00 GMT', 'figures': '#example#nini#', 'id': 5,
             'is_draft': False, 'text': 'very old story (11 11 2011)'}])

    def test_existing_story(self):
        response = self.client.get('/stories/1')
        body = json.loads(str(response.data, 'utf8'))
        test_story = Story.query.filter_by(id=1).first()
        self.assertEqual(body['text'], test_story.to_json()['text'])
        self.assertEqual(body['author_id'], test_story.to_json()['author_id'])

    def test_non_existing_story(self):
        response = self.client.get('/stories/50')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 404)
        self.assertEqual(body['description'], 'Specified story not found')

    # Testing that the oldest story per user is contained in the resulting stories
    def test_latest_story(self):
        response = self.client.get('/stories/latest')
        body = json.loads(str(response.data, 'utf8'))
        self.assertEqual(body,
                         [
                             {'author_id': 1, 'date': 'Sun, 20 Oct 2019 00:00:00 GMT', 'figures': '#example#admin#',
                              'id': 1,
                              'is_draft': False, 'text': 'Trial story of example admin user :)'},
                             {'author_id': 2, 'date': 'Sun, 13 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#',
                              'id': 3,
                              'is_draft': False, 'text': 'You should see this one in /latest'},
                             {'author_id': 3, 'date': 'Fri, 11 Nov 2011 00:00:00 GMT', 'figures': '#example#nini#',
                              'id': 5,
                              'is_draft': False, 'text': 'very old story (11 11 2011)'}
                         ]
                         )

    # Testing range story with possible inputs
    def test_range_story(self):
        # Testing range without parameters
        # Expected behaviour: it should return ALL the stories
        response = self.client.get('/stories/range')
        all_stories = db.session.query(Story).filter_by(is_draft=False).all()
        all_storiesJ = jsonify([story.to_json() for story in all_stories])
        self.assertStatus(response, 200)
        self.assertEqual(response.data, all_storiesJ.data)

        # Testing range with only one parameter (begin)
        # Expected behaviour: it should return the stories starting from specified date to TODAY
        response = self.client.get('/stories/range?begin=2013-10-10')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 200)
        self.assertEqual(body, [
            {'author_id': 1, 'date': 'Sun, 20 Oct 2019 00:00:00 GMT', 'figures': '#example#admin#', 'id': 1,
             'is_draft': False, 'text': 'Trial story of example admin user :)'},
            {'author_id': 2, 'date': 'Thu, 10 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 2,
             'is_draft': False, 'text': 'Old story (dont see this in /latest)'},
            {'author_id': 2, 'date': 'Sun, 13 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 3,
             'is_draft': False, 'text': 'You should see this one in /latest'}])

        # Testing range with only one parameter (end)
        # Expected behaviour: it should return all the stories BEFORE the specified date
        response = self.client.get('/stories/range?end=2013-10-10')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 200)
        self.assertEqual(body, [
            {'author_id': 3, 'date': 'Fri, 11 Nov 2011 00:00:00 GMT', 'figures': '#example#nini#', 'id': 5,
             'is_draft': False, 'text': 'very old story (11 11 2011)'}])

        # Testing range with begin date > end date
        response = self.client.get('/stories/range?begin=2012-12-12&end=2011-10-10')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'], 'Begin date cannot be higher than End date')

        # Testing range with wrong url parameters
        response = self.client.get('/stories/range?begin=abc&end=abc')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'], 'Wrong URL parameters')

        # Testing range with a valid request
        # Expected behaviour: return all the stories between the specified dates
        response = self.client.get('/stories/range?begin=2012-10-15&end=2020-10-10')
        body = json.loads(str(response.data, 'utf8'))
        print(body)
        self.assertEqual(body, [
            {'author_id': 1, 'date': 'Sun, 20 Oct 2019 00:00:00 GMT', 'figures': '#example#admin#', 'id': 1,
             'is_draft': False, 'text': 'Trial story of example admin user :)'},
            {'author_id': 2, 'date': 'Thu, 10 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 2,
             'is_draft': False, 'text': 'Old story (dont see this in /latest)'},
            {'author_id': 2, 'date': 'Sun, 13 Oct 2019 00:00:00 GMT', 'figures': '#example#abc#', 'id': 3,
             'is_draft': False, 'text': 'You should see this one in /latest'}]
                         )

    def test_get_draft(self):
        # Testing writing of a valid draft story
        response = self.client.get('/stories/new/write/4?user_id=3')
        self.assertStatus(response, 200)
        self.assertEqual(response.data.decode('utf8'), 'Session  to continue writing a draft OK')

        # Testing writing of other user's draft
        response = self.client.get('/stories/new/write/4?user_id=2')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'],
                         'Request is invalid, check if you are the author of the story and it is still a draft')

        # Testing writing of an already published story
        response = self.client.get('/stories/new/write/3?user_id=3')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'],
                         'Request is invalid, check if you are the author of the story and it is still a draft')

    def test_write_story(self):
        # Testing invalid request
        payload = {'text': 'my cat is drinking a gin tonic with my neighbour\'s dog', 'as_draft': 'a', 'user': 'b'}
        response = self.client.post('/stories/new/write', data=json.dumps(payload), content_type='application/json')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'], 'Wrong parameters')

        # Testing publishing invalid story
        with self.client.session_transaction() as session:
            session.clear()
            session['figures'] = ['beer', 'cat', 'dog']
        payload = {'text': 'my cat is drinking a gin tonic with my neighbour\'s dog', 'as_draft': False, 'user_id': '1'}
        response = self.client.post('/stories/new/write', data=json.dumps(payload), content_type='application/json')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 422)
        self.assertEqual(body['description'], 'Your story doesn\'t contain all the words. Missing: beer ')

        # Testing publishing valid story
        payload = {'text': 'my cat is drinking a beer with my neighbour\'s dog', 'as_draft': False, 'user_id': '1'}
        response = self.client.post('/stories/new/write', data=json.dumps(payload), content_type='application/json')
        self.assertStatus(response, 201)
        self.assertEqual(response.data.decode('utf8'), 'New story has been published')

        # Testing saving a new story as draft
        with self.client.session_transaction() as session:
            session.clear()
            session['figures'] = ['beer', 'cat', 'dog']
        payload2 = {'text': 'my cat is drinking', 'as_draft': True, 'user_id': '1'}
        response = self.client.post('/stories/new/write', data=json.dumps(payload2), content_type='application/json')
        self.assertStatus(response, 201)
        self.assertEqual(response.data.decode('utf8'), 'Draft created')

        # Testing saving a draft again
        count = db.session.query(Story).count()
        with self.client.session_transaction() as session:
            session['figures'] = ['beer', 'cat', 'dog']
            session['id_story'] = 6
        response = self.client.post('/stories/new/write', data=json.dumps(payload2), content_type='application/json')
        self.assertStatus(response, 200)
        self.assertEqual(response.data.decode('utf8'), 'Draft updated')
        # No items added
        q = db.session.query(Story).filter(Story.id == count + 1).first()
        self.assertEqual(q, None)

        # Testing publishing a draft story
        with self.client.session_transaction() as session:
            session['figures'] = ['beer', 'cat', 'dog']
            session['id_story'] = 6
        payload3 = {'text': 'my cat is drinking dog and beer', 'as_draft': False, 'user_id': '1'}
        response = self.client.post('/stories/new/write', data=json.dumps(payload3), content_type='application/json')
        self.assertStatus(response, 201)
        self.assertEqual(response.data.decode('utf8'), 'Draft has been published')
        q = db.session.query(Story).filter(Story.id == count + 1).first()
        self.assertEqual(q, None)
        q = db.session.query(Story).filter(Story.id == 6).first()
        self.assertEqual(q.is_draft, False)

    def test_delete_story(self):
        # Deleting the story of another user
        response = self.client.post('/stories/delete/1?user_id=2')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 400)
        self.assertEqual(body['description'],
                         'Request is invalid, check if you are the author of the story and the id is a valid one')

        # Deleting your story
        response = self.client.post('/stories/delete/1?user_id=1')
        self.assertStatus(response, 200)
        self.assertEqual(response.data.decode('utf8'),
                         'Story has been deleted')


class TestRandomRecentStory(flask_testing.TestCase):
    app = None

    # First thing called
    def create_app(self):
        global app
        app = create_app(database=TEST_DB)
        return app

    # Set up database for testing here
    def setUp(self) -> None:
        with app.app_context():
            # Create a not recent story by Admin2
            example = Story()
            example.text = 'This is a story about the end of the world'
            example.date = datetime.datetime.strptime('2012-12-12', '%Y-%m-%d')
            example.author_id = 2
            example.figures = '#story#world#'
            example.is_draft = False
            db.session.add(example)
            db.session.commit()

            # Create a recent story saved as draft by Admin2
            example = Story()
            example.text = 'This story is just a draft'
            example.date = datetime.datetime.now()
            example.author_id = 2
            example.figures = '#story#draft#'
            example.is_draft = True
            db.session.add(example)
            db.session.commit()

            # Create a recent story by Admin
            example = Story()
            example.text = 'Just another story'
            example.date = datetime.datetime.now()
            example.author_id = 1
            example.figures = '#dice#example#'
            example.is_draft = False
            db.session.add(example)
            db.session.commit()

    def test_random_recent_story(self):
        # Random recent story as anonymous user
        response = self.client.get('/stories/random')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 200)
        self.assertEqual(body['text'], 'Just another story')

        # No recent stories
        response = self.client.get('/stories/random?user_id=1')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 404)
        self.assertEqual(body['description'], 'There are no recent stories by other users')

        # Create a new recent story by Admin2
        example = Story()
        example.text = 'This is a valid recent story'
        example.date = datetime.datetime.now()
        example.author_id = 2
        example.figures = 'story#recent'
        example.is_draft = False
        db.session.add(example)
        db.session.commit()

        # Get the only recent story not written by Admin
        response = self.client.get('/stories/random?user_id=1')
        body = json.loads(str(response.data, 'utf8'))
        self.assertStatus(response, 200)
        self.assertEqual(body['text'], 'This is a valid recent story')
