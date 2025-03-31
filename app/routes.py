from flask import Blueprint, flash, render_template, request, redirect, url_for, session, Response as FlaskResponse
#from flask_sse import sse
from . import db, create_app
from .services import story_service, question_service, story_builder_service, llm_service
from .models import Template, Story, Question, Model, Provider, Response
import time
import json
from threading import Thread


# Create a blueprint for the routes
bp = Blueprint('main', __name__)
progress_tracker = {'progress': 0}

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
#             #stories = [db.session.query(Story).get(story_id) for story_id in generated_stories_ids]
#             session['generated_story_ids'] = generated_stories_ids
#             return redirect(url_for('main.display_generated_stories'))
#         return render_template('generate_stories.html', template=template, fields=fields, missing_fields=missing_fields, num_stories=num_stories)
#     return redirect(url_for('main.see_all_templates'))
@bp.route('/generate_stories', methods=['GET', 'POST'])
def generate_stories():
    if request.method == 'POST':
        # For form submissions (field updates, generation)
        template_id = request.form.get('template_id')
        print("Form data received:")
        print("generate button:", "generate" in request.form)
        print("update_fields button:", "update_fields" in request.form)
        print("template_id:", request.form.get('template_id'))
        print("field_data:", request.form.get('field_data'))
        
        # Check if we're updating the fields or generating stories
        if 'update_fields' in request.form:
            # Process field updates
            field_data = json.loads(request.form.get('field_data', '{}'))
            story_builder_service.update_field_words(field_data)
            flash('Fields updated successfully!', 'success')
            return redirect(url_for('main.generate_stories', template_id=template_id))
            
        elif 'generate' in request.form:
            # Generate stories with current fields
            try:
                # Parse the field data from the form
                field_data = json.loads(request.form.get('field_data', '{}'))
                story_builder_service.update_field_words(field_data) #I think if stories are being generated the user would expect the words and fields to be saved also.
                
                
                # Pass the field data to the generate_stories function
                generated_story_ids = story_builder_service.generate_stories(template_id, field_data)
                session['generated_story_ids'] = generated_story_ids
                return redirect(url_for('main.display_generated_stories'))
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print the full error stack
                flash(f'Error generating stories: {str(e)}', 'danger')
                return redirect(url_for('main.generate_stories', template_id=template_id))
    
    # GET request - display the form
    templates = story_builder_service.get_all_templates()
    
    # Get template_id either from query params (GET) or form data (POST)
    template_id = request.args.get('template_id') or request.form.get('template_id')
    
    fields = {}
    missing_fields = []
    template = None
    
    if template_id:
        template = db.session.query(Template).get(template_id)
        fields, missing_fields = story_builder_service.get_template_fields(template_id)

        print("===== DEBUG INFO =====")
        print("Template ID:", template_id)
        print("Fields from database:", fields)
        for field_name, words in fields.items():
            print(f"Field '{field_name}' has {len(words)} words: {words[:5]}...")
        print("Missing fields:", missing_fields)
        print("======================")
    
    return render_template(
        'generate_stories_drag_and_drop.html', 
        templates=templates, 
        selected_template_id=template_id,
        template=template, 
        fields=fields,
        missing_fields=missing_fields
    )

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
        # Store the selected parameters in the session
        parameters = {param: request.form.get(param) for param in request.form}
        session['parameters'] = parameters

        # Redirect to the loading page
        return redirect(url_for('main.loading'))
    
    else:
        model_id = session.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        parameters = model.parameters
        print("Time to select parameters")
        return render_template('select_parameters.html', parameters=parameters)

@bp.route('/progress')
def progress():
    def generate():
        while True:
            # Use only the global progress_tracker, not the session
            progress = progress_tracker.get('progress', 0)
            response_ids = progress_tracker.get('response_ids', [])
            
            if response_ids or progress >= 100:
                yield f"data: {json.dumps({'status': 'complete', 'progress': 100})}\n\n"
                break
            else:
                yield f"data: {json.dumps({'status': 'incomplete', 'progress': progress})}\n\n"
                time.sleep(1)
                
    return FlaskResponse(generate(), mimetype='text/event-stream')

@bp.route('/loading')
def loading():
    # Extract necessary session data
    model_id = session.get('model_id')
    story_ids = session.get('story_ids', [])
    question_id = session.get('question_id')
    parameters = session.get('parameters', {})

    # Store these in the session for the background process
    session['processing_data'] = {
        'model_id': model_id,
        'story_ids': story_ids,
        'question_id': question_id,
        'parameters': parameters
    }
    
    # Initialize progress tracker with empty response_ids
    progress_tracker['progress'] = 0
    progress_tracker['response_ids'] = []
    progress_tracker['processing'] = False
    
    return render_template('loading.html')

@bp.route('/start_processing')
def start_processing():
    # Get the data stored in the session
    processing_data = session.get('processing_data', {})
    model_id = processing_data.get('model_id')
    story_ids = processing_data.get('story_ids', [])
    question_id = processing_data.get('question_id')
    parameters = processing_data.get('parameters', {})
    
    # Mark as processing
    progress_tracker['processing'] = True
    
    # Start the LLM call
    response_data = llm_service.prepare_and_call_llm(
        model_id, story_ids, question_id, parameters, 
        progress_callback=lambda p: progress_tracker.__setitem__('progress', p)
    )
    
    # Extract response IDs
    response_ids = [response['response_id'] for response in response_data.values()]
    
    # Store in both progress_tracker and session
    progress_tracker['response_ids'] = response_ids
    session['response_ids'] = response_ids
    
    # Set progress to 100% and mark as done
    progress_tracker['progress'] = 100
    progress_tracker['processing'] = False
    
    return {"status": "complete"}

def update_progress():
    """Background thread that just sleeps until processing is done."""
    while progress_tracker['progress'] < 100:
        time.sleep(0.5)  # Wait for half a second

# def process_stories(model_id, story_ids, question_id, parameters):
#     app = create_app()
#     with app.app_context():
#         response_data, progress, response_ids = llm_service.prepare_and_call_llm(model_id, story_ids, question_id, parameters)
#         print("About to print response_data")
#         print(response_data)
#         # Store progress and response IDs in the session
#         session['progress'] = progress
#         session['response_ids'] = response_ids

@bp.route('/check_status')
def check_status():
    # Check the progress of processing
    progress = session.get('progress', 0)
    response_ids = session.get('response_ids', [])
    if response_ids:
        return {"status": "complete", "progress": 100}
    else:
        return {"status": "incomplete", "progress": progress}

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