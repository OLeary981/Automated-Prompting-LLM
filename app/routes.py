from flask import Blueprint, flash, render_template, request, redirect, url_for, session
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

# @bp.route('/generate_stories', methods=['GET', 'POST'])
# def generate_stories():
#     template_id = request.args.get('template_id') or request.form.get('template_id')
#     if template_id:
#         template = db.session.query(Template).get(template_id)
#         fields, missing_fields = story_builder_service.get_template_fields(template_id)
#         permutations = story_builder_service.generate_permutations(fields)
#         num_stories = len(permutations)
#         if request.method == 'POST' and 'generate' in request.form:
#             generated_stories_ids = story_builder_service.generate_stories(template_id)
#             story_contents = {story_id: db.session.query(Story).get(story_id).content for story_id in generated_stories_ids}
#             return render_template('generated_stories.html', story_ids=generated_stories_ids, story_contents=story_contents)
#         return render_template('generate_stories.html', template=template, fields=fields, missing_fields=missing_fields, num_stories=num_stories)
#     return redirect(url_for('main.see_all_templates'))

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
            #stories = [db.session.query(Story).get(story_id) for story_id in generated_stories_ids]
            session['generated_story_ids'] = generated_stories_ids
            return redirect(url_for('main.display_generated_stories'))
        return render_template('generate_stories.html', template=template, fields=fields, missing_fields=missing_fields, num_stories=num_stories)
    return redirect(url_for('main.see_all_templates'))

@bp.route('/display_generated_stories', methods=['GET'])
def display_generated_stories():
    session['story_ids'] = session.get('generated_story_ids', [])
    story_ids = session.get('generated_story_ids', [])
    stories = [db.session.query(Story).get(story_id) for story_id in story_ids]    
    return render_template('display_generated_stories.html', stories=stories)

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
            print(session)
        return redirect(url_for('main.select_parameters'))
    else:
        models = db.session.query(Model).join(Provider).all()
        return render_template('select_model.html', models=models)

@bp.route('/select_story', methods=['GET', 'POST'])
def select_story():
    if request.method == 'POST':
        if 'deselect_story_id' in request.form:
            # Deselect the story
            story_id = request.form.get('deselect_story_id')
            story_ids = session.get('story_ids', [])
            if story_id in story_ids:
                story_ids.remove(story_id)
            session['story_ids'] = story_ids
            print(session)
        else:
            # Select the story
            story_id = request.form.get('story_id')
            story = db.session.query(Story).filter_by(story_id=story_id).first()
            if story:
                story_ids = session.get('story_ids', [])
                if story_id not in story_ids:
                    story_ids.append(story_id)
                session['story_ids'] = story_ids
                print(session)
        return redirect(url_for('main.select_story'))
    else:
            story_ids = session.get('story_ids', [])
            if story_ids:
                # Display the selected stories
                selected_stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
                all_stories = story_service.get_all_stories()
                return render_template('selected_stories.html', selected_stories=selected_stories, all_stories=all_stories)
            else:
                # Display the list of available stories for selection
                stories = story_service.get_all_stories()
                print("reaching select stories")
                return render_template('select_story.html', stories=stories)

#route that worked fairly well before trying to add deselection of story
# @bp.route('/select_story', methods=['GET', 'POST'])
# def select_story():
#     if request.method == 'POST':
#         story_id = request.form.get('story_id')
#         story = db.session.query(Story).filter_by(story_id=story_id).first()
#         if story:
#             # Add the selected story_id to the list of story_ids in the session
#             story_ids = session.get('story_ids', [])
#             if story_id not in story_ids:
#                 story_ids.append(story_id)
#             session['story_ids'] = story_ids
#             print(session)
#         return redirect(url_for('main.select_story'))
#     else:
#         story_ids = session.get('story_ids', [])
#         if story_ids:
#             # Display the selected stories
#             selected_stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
#             return render_template('selected_stories.html', selected_stories=selected_stories)
#         else:
#             # Display the list of available stories for selection
#             stories = story_service.get_all_stories()
#             print("reaching select stories")
#             return render_template('select_story.html', stories=stories)


@bp.route('/select_question', methods=['GET', 'POST'])
def select_question():
    if request.method == 'POST':
        question_id = request.form.get('question_id')
        if question_id:
            session['question_id'] = question_id
            print("Stored question_id in session:", session['question_id'])
        return redirect(url_for('main.select_model'))  # Next step
    else:
        questions = llm_service.get_all_questions()
        return render_template('select_question.html', questions=questions)


@bp.route('/select_parameters', methods=['GET', 'POST'])
def select_parameters():
    if request.method == 'POST':        
        print("About to send prompt to llm")
        response_data = llm_service.prepare_and_call_llm(request, session) #will do all the stories and hany everything up until finished
        print(response_data)

        session['responses'] = response_data  # Store responses for later access
        

        return redirect(url_for('main.loading')) # in wrong place
    
    else:
        model_id = session.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        parameters = model.parameters
        print("Time to select parameters")
        return render_template('select_parameters.html', parameters=parameters)

@bp.route('/loading')
def loading():
    return render_template('loading.html')

@bp.route('/check_status')
def check_status():
    # Check if the processing is complete
    response_ids = session.get('response_ids', [])
    if response_ids:
        return {"status": "complete"}
    else:
        return {"status": "incomplete"}

@bp.route('/llm_response', methods=['GET', 'POST'])
def llm_response():
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        if response_id:
            flagged_for_review = f'flagged_for_review_{response_id}' in request.form
            review_notes = request.form.get(f'review_notes_{response_id}', '')

            response = db.session.query(Response).get(response_id)
            if response:
                response.flagged_for_review = flagged_for_review
                response.review_notes = review_notes
                db.session.commit()
                flash(f'Response {response_id} updated successfully!', 'success')
            else:
                flash(f'Error: Response {response_id} not found.', 'danger')

        return redirect(url_for('main.llm_response'))

    # Fetch response details
    response_ids = session.get('response_ids', [])
    story_ids = session.get('story_ids', [])
    stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
    responses = [db.session.query(Response).get(response_id) for response_id in response_ids]

    response_details = []
    for response in responses:
        if response is None:
            flash('One or more responses not found.', 'danger')
            return redirect(url_for('main.index'))
        response_details.append({
            'response_id': response.response_id,
            'response_content': response.response_content,
            'flagged_for_review': response.flagged_for_review,
            'review_notes': response.review_notes
        })

    # Retrieve model, provider, and question
    question_id = session.get('question_id')
    question = db.session.query(Question).get(question_id).content if question_id else None

    return render_template('llm_response.html', 
                           combined_data=zip(stories, response_details),
                           model=session.get('model'), 
                           provider=session.get('provider'), 
                           question=question)


@bp.route('/clear_session', methods=['GET'])
def clear_session():
    print("Session before printing:")
    print(session)
    print("Clearing session")
    session.clear()
    flash('Session data cleared!', 'success')
    print(session)
    return redirect(url_for('main.index'))