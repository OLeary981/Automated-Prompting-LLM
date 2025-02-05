from flask import Blueprint, flash, render_template, request, redirect, url_for, session

from app.services.response_review_service import flag_response
from . import db
from .services import story_service, question_service, story_builder_service, llm_service
from .models import Template, Story, Question, Model, Provider, Response

# Create a blueprint for the routes
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
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

@bp.route('/see_all_templates')
def see_all_templates():
    templates = story_builder_service.get_all_templates()
    return render_template('see_all_templates.html', templates=templates)

@bp.route('/add_template', methods=['POST'])
def add_template():
    template_content = request.form.get('template_content')
    if template_content:
        new_template = Template(content=template_content)
        db.session.add(new_template)
        db.session.commit()
    return redirect(url_for('main.see_all_templates'))

@bp.route('/generate_stories', methods=['GET', 'POST'])
def generate_stories():
    template_id = request.args.get('template_id') or request.form.get('template_id')
    if template_id:
        template = db.session.query(Template).get(template_id)
        fields, missing_fields = story_builder_service.get_template_fields(template_id)
        permutations = story_builder_service.generate_permutations(fields)
        num_stories = len(permutations)
        if request.method == 'POST' and 'generate' in request.form:
            generated_stories_ids = story_builder_service.generate_stories(template_id)
            story_contents = {story_id: db.session.query(Story).get(story_id).content for story_id in generated_stories_ids}
            return render_template('generated_stories.html', story_ids=generated_stories_ids, story_contents=story_contents)
        return render_template('generate_stories.html', template=template, fields=fields, missing_fields=missing_fields, num_stories=num_stories)
    return redirect(url_for('main.see_all_templates'))

@bp.route('/add_word', methods=['POST'])
def add_word():
    field_name = request.form.get('field_name')
    new_words = request.form.get('new_words')
    template_id = request.form.get('template_id')
    if field_name and new_words:
        story_builder_service.add_words_to_field(field_name, new_words)
    return redirect(url_for('main.generate_stories', template_id=template_id))

@bp.route('/select_model', methods=['GET', 'POST'])
def select_model():
    if request.method == 'POST':
        model_id = request.form.get('model_id')
        model = db.session.query(Model).filter_by(model_id=model_id).first()
        if model:
            print("Model found, setting model and provider in session")
            session['model_id'] = model_id
            session['model'] = model.name
            session['provider'] = model.provider.provider_name
        return redirect(url_for('main.select_story'))
    else:
        models = db.session.query(Model).join(Provider).all()
        return render_template('select_model.html', models=models)

@bp.route('/select_story', methods=['GET', 'POST'])
def select_story():
    if request.method == 'POST':
        story_id = request.form.get('story_id')
        story = db.session.query(Story).filter_by(story_id=story_id).first()
        if story:
            session['story_id'] = story_id
            session['story'] = story.content
        return redirect(url_for('main.select_question'))
    else:
        stories = llm_service.get_all_stories()
        return render_template('select_story.html', stories=stories)

@bp.route('/select_question', methods=['GET', 'POST'])
def select_question():
    if request.method == 'POST':
        question_id = request.form.get('question_id')
        question = db.session.query(Question).filter_by(question_id=question_id).first()
        if question:
            session['question_id'] = question_id
            session['question'] = question.content
        return redirect(url_for('main.select_parameters'))
    else:
        questions = llm_service.get_all_questions()
        return render_template('select_question.html', questions=questions)


@bp.route('/select_parameters', methods=['GET', 'POST'])
def select_parameters():
    if request.method == 'POST':
        response_content = llm_service.prepare_and_call_llm(request, session)
        
        # Extract the necessary information from the session
        story = session.get('story')
        question = session.get('question')
        model = session.get('model')
        provider = session.get('provider')
        
        # Store the response_id and other relevant data in the session
        response_id = response_content.get('response_id')  # Assuming response_content contains response_id
        session['response_id'] = response_id
        session['response_content'] = response_content.get('response')
        
        return redirect(url_for('main.llm_response'))
    else:
        model_id = session.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        parameters = model.parameters
        return render_template('select_parameters.html', parameters=parameters)
    

@bp.route('/llm_response', methods=['GET', 'POST'])
def llm_response():
    if request.method == 'POST':
        response_id = session.get('response_id')
        flagged_for_review = 'flagged_for_review' in request.form
        review_notes = request.form.get('review_notes')
        if flag_response(response_id, flagged_for_review, review_notes):
            flash('Response flagged for review successfully!', 'success')
        else:
            flash('Error flagging response for review.', 'danger')
        return redirect(url_for('main.llm_response'))
    
    response_id = session.get('response_id')
    story = session.get('story')
    question = session.get('question')
    model = session.get('model')
    provider = session.get('provider')
    response_content = session.get('response_content')
    
    # Retrieve flag status and review notes from session
    response = Response.query.get(response_id)
    flagged_for_review = response.flagged_for_review
    review_notes = response.review_notes    
    
    return render_template('llm_response.html', response_id=response_id, story=story, question=question, model=model, provider=provider, response=response_content, flagged_for_review=flagged_for_review, review_notes=review_notes)