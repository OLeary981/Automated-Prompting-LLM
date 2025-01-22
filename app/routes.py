from flask import Blueprint, render_template, request, redirect, url_for, session
from . import db
from .services import story_service, question_service, story_builder_service, llm_service
from .models import Template, Story, Question, Model, Provider

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

@bp.route('/send_prompt_to_llm')
def send_prompt_to_llm():
    models = db.session.query(Model).join(Provider).all()
    return render_template('send_prompt_to_llm.html', models=models)

@bp.route('/select_story/<int:model_id>')
def select_story(model_id):
    session['model_id'] = model_id
    stories = llm_service.get_all_stories()
    return render_template('select_story.html', stories=stories)

@bp.route('/select_question/<int:story_id>')
def select_question(story_id):
    session['story_id'] = story_id
    questions = llm_service.get_all_questions()
    return render_template('select_question.html', questions=questions)


@bp.route('/select_parameters/<int:question_id>', methods=['GET', 'POST'])
def select_parameters(question_id):
    if request.method == 'POST':
        session['question_id'] = question_id
        response = llm_service.prepare_and_call_llm(request, session)
        return render_template('llm_response.html', response=response)
    else:
        model_id = session.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        parameters = model.parameters
        session['question_id'] = question_id
        return render_template('select_parameters.html', parameters=parameters)
        
