from flask import Blueprint, render_template, request, redirect, url_for
from . import db
from .models import Story

# Create a blueprint for the routes
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    print("Hello, can you hear me?")
    return render_template('index.html')

@bp.route('/add_story', methods=['GET', 'POST'])
def add_story():
    print("Now we are on the add_story route")
    if request.method == 'POST':
        # Get the story content from the form
        content = request.form.get('story_content')
        print(f"Content received: {content}")
        
        if content:
            # Create a new Story object and add it to the database
            new_story = Story(content=content)
            db.session.add(new_story)
            db.session.commit()

            story_id=new_story.story_id
            print(f"Story ID: {story_id}")

        # Redirect to the home page after adding the story
        return redirect(url_for('main.index'))
    
    # Render the add_story.html template for GET requests
    return render_template('add_story.html')

@bp.route('/see_all_stories')
def see_all_stories():
    stories = Story.query.all()
    return render_template('see_all_stories.html', stories=stories)

@bp.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if request.method == 'POST':
        question_content = request.form['question_content']
        question = Question(content=question_content)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_question.html')

@bp.route('/see_all_questions')
def see_all_questions():
    questions = Question.query.all()
    return render_template('see_all_questions.html', questions=questions)
