import datetime
import itertools
import os
import re
import string
from builtins import hasattr
from random import randint

from flask import Blueprint, redirect, render_template, request, make_response, url_for, flash, jsonify, abort
from flakon import SwaggerBlueprint
from flask import session
from flask_login import (current_user, login_required)
from sqlalchemy import and_, func, desc

from StoriesService.database import db, Story
from StoriesService.urls import *

YML = os.path.join(os.path.dirname(__file__), '..', 'static', 'api.yaml')
stories = SwaggerBlueprint('stories', '__name__', swagger_spec=YML)


@stories.operation('getStories')
def _stories():
    all_stories = db.session.query(Story).order_by(desc(Story.date)).filter_by(is_draft=False).all()
    return jsonify([story.to_json() for story in all_stories])


# Gets the last NON-draft story for each registered user
@stories.operation('getLatestStories')
def _latest():
    listed_stories = db.session.query(Story).order_by(desc(Story.date)).filter_by(is_draft=False).order_by(func.max(Story.date)).group_by(
        Story.author_id).all()
    return jsonify([story.to_json() for story in listed_stories])


# Searches for stories that were made in a specific range of time
@stories.operation('getRangeStories')
def _range():
    # Get the two parameters
    begin = request.args.get('begin')
    end = request.args.get('end')

    # Construct begin_date and end_date (given or default)
    try:
        if begin and len(begin) > 0:
            begin_date = datetime.datetime.strptime(begin, '%Y-%m-%d')
        else:
            begin_date = datetime.datetime.min
        if end and len(end) > 0:
            end_date = datetime.datetime.strptime(end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            # Here .replace is needed because of solar/legal hour!
            # Stories are written at time X in db, and searched at time X-1
            end_date = datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)
    # If a strptime fails getting the date, it means at least one of the parameters was invalid
    except ValueError:
        abort(400, "Wrong URL parameters")

    # If dates were valid, I still have to check if the request is a valid one
    if begin_date > end_date:
        abort(400, "Begin date cannot be higher than End date")

    # Returns all the NON-draft stories that are between the requested dates
    listed_stories = db.session.query(Story).filter(Story.date >= begin_date).filter(Story.date <= end_date).filter(
        Story.is_draft == False)

    return jsonify([story.to_json() for story in listed_stories])


# Get a random story written by other users in the last three days
@stories.operation('getRandomStory')
def _random_story():
    # get all the stories written in the last three days by other users
    user_id = request.args.get('user_id')
    begin = (datetime.datetime.now() - datetime.timedelta(3)).date()
    if user_id and user_id.isdigit():
        q = db.session.query(Story).filter(Story.date >= begin,
                                           Story.author_id != user_id,
                                           Story.is_draft == False)
    else:
        q = db.session.query(Story).filter(Story.date >= begin, Story.is_draft == False)
    recent_stories = q.all()
    # pick a random story from them
    if len(recent_stories) == 0:
        abort(404, 'There are no recent stories by other users')
    else:
        pos = randint(0, len(recent_stories) - 1)
        return jsonify(recent_stories[pos].to_json())


# Open a story functionality (1.8)
@stories.operation('getStory')
def _open_story(id_story):
    q = db.session.query(Story).filter(Story.id == id_story).all()
    if q:
        return jsonify(q[0].to_json())
    else:
        abort(404, 'Specified story not found')


# Get the form to write a new story or continue a draft
# Publish the story or save as draft
@stories.operation('writeDraft')
def _get_draft(id_story=None):
    # Setting session to modify draft
    if 'GET' == request.method and id_story is not None:
        user_id = request.args.get('user_id')
        story = Story.query.filter(Story.id == id_story).first()
        if user_id and user_id.isdigit() and story is not None and story.author_id == int(user_id) and story.is_draft:
            session['figures'] = story.figures.split('#')
            session['figures'] = session['figures'][1:-1]
            session['id_story'] = story.id
            return make_response('Session  to continue writing a draft OK')
        else:
            abort(400, 'Request is invalid, check if you are the author of the story and it is still a draft')


@stories.operation('writeStory')
def _write_story(id_story=None, message='', status=200):
    if 'POST' == request.method:
        requestj = request.get_json(request)
        try:
            text = requestj['text']
            draft = requestj['as_draft']
            user_id = requestj['user_id']
            if draft:
                if 'id_story' in session:
                    # Update a draft
                    date_format = "%Y %m %d %H:%M"
                    date = datetime.datetime.strptime(datetime.datetime.now().strftime(date_format), date_format)
                    db.session.query(Story).filter_by(id=session['id_story']).update({'text': text,                                                                 'date': date})
                    db.session.commit()
                    session.pop('id_story')
                    status = 200
                    message = 'Draft updated'
                else:
                    # Save new story as draft
                    new_story = Story()
                    new_story.author_id = user_id
                    new_story.figures = '#' + '#'.join(session['figures']) + '#'
                    new_story.is_draft = True
                    new_story.text = text
                    db.session.add(new_story)
                    db.session.commit()
                    status = 201
                    message = 'Draft created'
                session.pop('figures')
            else:
                # Check validity
                dice_figures = session['figures'].copy()
                trans = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
                new_s = text.translate(trans).lower()
                story_words = new_s.split()
                for w in story_words:
                    if w in dice_figures:
                        dice_figures.remove(w)
                        if not dice_figures:
                            break
                if len(dice_figures) > 0:
                    message = 'Your story doesn\'t contain all the words. Missing: '
                    for w in dice_figures:
                        message += w + ' '
                    abort(422, message)
                else:
                    if 'id_story' in session:
                        # Publish a draft
                        date_format = "%Y %m %d %H:%M"
                        date = datetime.datetime.strptime(datetime.datetime.now().strftime(date_format), date_format)
                        db.session.query(Story).filter_by(id=session['id_story']).update(
                            {'text': text, 'date': date, 'is_draft': False})
                        db.session.commit()
                        session.pop('id_story')
                        status = 201
                        message = 'Draft has been published'
                    else:
                        # Publish a new story
                        new_story = Story()
                        new_story.author_id = user_id
                        new_story.figures = '#' + '#'.join(session['figures']) + '#'
                        new_story.is_draft = False
                        new_story.text = text
                        db.session.add(new_story)
                        db.session.commit()
                        status = 201
                        message = 'New story has been published'
                    # TODO: chiamare inizializzaione delle reactions
                    session.pop('figures')
            return make_response(message, status)
        # If values in request body aren't well-formed
        except (ValueError, KeyError):
            abort(400, 'Wrong parameters')

@stories.operation('getStoriesStatistics')
def _stories_stats(user_id):
    all_stories = Story.query.filter(Story.author_id==user_id).all()
    num_stories = len(all_stories)
    tot_num_dice = 0
    avg_dice = 0.0

    for story in all_stories:
        rolled_dice = story.figures.split('#')
        rolled_dice = rolled_dice[1:-1]
        tot_num_dice += len(rolled_dice)

    if num_stories is not 0:
        avg_dice = round(tot_num_dice / num_stories, 2)

    result = {
        'num_stories': num_stories,
        'tot_num_dice': tot_num_dice,
        'avg_dice': avg_dice
    }

    return jsonify(result)


# @stories.route('/stories/delete/<int:id_story>', methods=['POST'])
# @login_required
# def _manage_stories(id_story):
#     story_to_delete = Story.query.filter(Story.id == id_story)
#     if story_to_delete.first().author_id != current_user.id:
#         flash("Cannot delete other user's story", 'error')
#     else:
#
#         Reaction.query.filter(Reaction.story_id == id_story).delete()
#         Counter.query.filter(Counter.story_id == id_story).delete()
#         story_to_delete.delete()
#         db.session.commit()
#
#     return redirect(url_for("home.index"))

@stories.operation('deleteStory')
def _manage_stories(id_story):
    user_id = request.args.get('user_id')
    story_to_delete = Story.query.filter(Story.id == id_story)
    if not user_id or not user_id.isdigit() or story_to_delete.first().author_id != int(user_id):
        abort(400, 'Request is invalid, check if you are the author of the story and the id is a valid one')
    else:
        # TODO : cancellare reactions and counters relativi
        # Reaction.query.filter(Reaction.story_id == id_story).delete()
        # Counter.query.filter(Counter.story_id == id_story).delete()
        story_to_delete.delete()
        db.session.commit()

    return make_response('Story has been deleted')
