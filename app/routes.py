from flask import Blueprint, render_template, request, redirect, url_for
from . import db
from .models import Story, Question
from .services import story_service, question_service

# Create a blueprint for the routes
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    print("Hello, can you hear me?")
    return render_template('index.html')

@bp.route('/add_story', methods=['GET', 'POST'])
def add_story():
    if request.method == 'POST':
        content = request.form.get('story_content')
        if content:
            try:
                story_id = story_service.add_story(content)
                print(f"Story ID: {story_id}")
            except Exception as e:
                print(f"An error occurred: {e}")
        return redirect(url_for('main.index'))
    return render_template('add_story.html')

@bp.route('/see_all_stories')
def see_all_stories():
    stories = story_service.get_all_stories()
    return render_template('see_all_stories.html', stories=stories)

@bp.route('/see_all_questions')
def see_all_questions():
    questions = question_service.get_all_questions()
    return render_template('see_all_questions.html', questions=questions)

@bp.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if request.method == 'POST':
        question_content = request.form.get('question_content')
        if question_content:
            try:
                question_id = question_service.add_question(question_content)
                print(f"Question ID: {question_id}")
            except Exception as e:
                print(f"An error occurred: {e}")
        return redirect(url_for('main.index'))
    return render_template('add_question.html')
