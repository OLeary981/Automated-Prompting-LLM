import datetime
from flask import Blueprint, flash, render_template, request, redirect, url_for, session, jsonify, Response as FlaskResponse, send_file
from . import db, create_app
from .services import story_service, question_service, story_builder_service, llm_service, category_service
from .models import Template, Story, Question, Model, Provider, Response, StoryCategory, Prompt, Field
import time
import json
import threading
from threading import Thread
import asyncio
import uuid
import csv
import io

#Another silly change to check new branchv2

# Create a blueprint for the routes
bp = Blueprint('main', __name__)
processing_jobs = {}
_event_loop = None
_event_loop_lock = threading.Lock()

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/add_story', methods=['GET', 'POST'])
def add_story():
    if request.method == 'POST':
        content = request.form.get('story_content')
        new_category = request.form.get('new_category')
        selected_categories = request.form.getlist('categories')
        
        # Convert selected categories to integers
        category_ids = [int(cat_id) for cat_id in selected_categories if cat_id]
        
        if content:
            try:
                # Process new category if provided
                if new_category and new_category.strip():
                    new_category_id = category_service.add_category(new_category.strip())
                    if new_category_id not in category_ids:
                        category_ids.append(new_category_id)
                
                # Add story with categories
                story_id = story_service.add_story(content, category_ids)
                flash('Story added successfully!', 'success')
                print(f"Story ID: {story_id}")
            except Exception as e:
                flash(f'Error adding story: {str(e)}', 'danger')
                print(f"An error occurred: {e}")
        return redirect(url_for('main.see_all_stories'))
    
    # Get all existing categories for the form
    categories = category_service.get_all_categories()
    return render_template('add_story.html', categories=categories)

@bp.route('/manage_categories', methods=['GET', 'POST'])
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            category_name = request.form.get('category_name')
            if category_name and category_name.strip():
                try:
                    category_service.add_category(category_name.strip())
                    flash(f'Category "{category_name}" added successfully!', 'success')
                except Exception as e:
                    flash(f'Error adding category: {str(e)}', 'danger')
        
        # Could add edit/delete functionality here
        
        return redirect(url_for('main.manage_categories'))
    
    categories = category_service.get_all_categories()
    return render_template('manage_categories.html', categories=categories)

@bp.route('/see_all_stories')
def see_all_stories():
    # Get the search and filter parameters
    search_text = request.args.get('search_text', '')
    category_filter = request.args.get('category_filter', '')
    sort_by = request.args.get('sort_by', 'desc')  # Default to descending (newest first)
    
    # Get the current page from the request, default to page 1
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of stories per page

    # Start building the query
    query = db.session.query(Story).options(
        db.joinedload(Story.story_categories).joinedload(StoryCategory.category)
    )

    # Apply search filter if provided
    if search_text:
        query = query.filter(Story.content.ilike(f'%{search_text}%'))
    
    # Apply category filter if provided
    if category_filter:
        try:
            category_id = int(category_filter)
            query = query.join(StoryCategory).filter(StoryCategory.category_id == category_id)
        except (ValueError, TypeError):
            # Handle invalid category_filter value
            flash('Invalid category filter', 'warning')
    
    # Apply sorting based on the `id`
    if sort_by == 'asc':
        query = query.order_by(Story.story_id.asc())  # Oldest to most recent (lower ID first)
    else:
        query = query.order_by(Story.story_id.desc())  # Most recent to oldest (higher ID first)

    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    stories = pagination.items

    # Get all categories for the dropdown
    categories = category_service.get_all_categories()
    
    # Get currently selected story IDs from session
    selected_story_ids = session.get('story_ids', [])

    # Render the template with stories and pagination data
    return render_template(
        'see_all_stories.html',
        stories=stories,
        categories=categories,
        pagination=pagination,
        sort_by=sort_by,
        selected_story_ids=selected_story_ids
    )

@bp.route('/update_story_selection', methods=['POST'])
def update_story_selection():
    data = request.get_json()
    
    # Get the current selection from session
    selected_story_ids = session.get('story_ids', [])
    
    # Clear all selected stories
    if data.get('action') == 'clear_all':
        selected_story_ids = []
    
    # Select multiple stories at once (for batch operations)
    elif data.get('action') == 'select_multiple':
        story_ids = data.get('story_ids', [])
        for story_id in story_ids:
            if story_id not in selected_story_ids:
                selected_story_ids.append(story_id)
    
    # Handle individual toggle
    elif 'story_id' in data:
        story_id = str(data['story_id'])
        is_selected = data.get('selected', False)
        
        if is_selected and story_id not in selected_story_ids:
            selected_story_ids.append(story_id)
        elif not is_selected and story_id in selected_story_ids:
            selected_story_ids.remove(story_id)
    
    # Store updated selection in session
    session['story_ids'] = selected_story_ids
    
    return jsonify({
        'success': True,
        'selected_count': len(selected_story_ids),
        'selected_ids': selected_story_ids
    })

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
    # Current pagination and search code remains the same
    search_text = request.args.get('search_text', '')
    sort_by = request.args.get('sort_by', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Build the query
    query = db.session.query(Template)
    
    # Apply search filter if provided
    if search_text:
        query = query.filter(Template.content.ilike(f'%{search_text}%'))
    
    # Apply sorting
    if sort_by == 'asc':
        query = query.order_by(Template.template_id.asc())
    else:
        query = query.order_by(Template.template_id.desc())
    
    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    templates = pagination.items
    
    # Get all fields from the Field table
    fields = db.session.query(Field.field).order_by(Field.field).all()
    template_fields = [field[0] for field in fields]  # Extract field names from result tuples
    
    return render_template('see_all_templates.html', 
                          templates=templates, 
                          pagination=pagination, 
                          sort_by=sort_by,
                          template_fields=template_fields)

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
    if request.method == 'POST':
        # For form submissions (field updates, generation)
        template_id = request.form.get('template_id')

        if template_id: session['template_id'] = template_id

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
            return redirect(url_for('main.generate_stories'))
            
        elif 'generate' in request.form:
            # Generate stories with current fields
            try:
                # Parse the field data from the form
                field_data = json.loads(request.form.get('field_data', '{}'))
                story_builder_service.update_field_words(field_data)  # Save fields


                template_id = session.get('template_id')
                if not template_id:
                    flash('No template selected. Please select a template first.', 'danger')
                    return redirect(url_for('main.generate_stories'))
                
                # Process categories - both existing and new ones
                category_ids = []
                
                # Process existing categories
                selected_categories = request.form.getlist('story_categories')
                category_ids.extend([int(cat_id) for cat_id in selected_categories if cat_id])
                
                # Process new categories
                new_categories = request.form.getlist('new_categories')
                for new_cat in new_categories:
                    if new_cat.strip():
                        try:
                            cat_id = category_service.add_category(new_cat.strip())
                            category_ids.append(cat_id)
                        except Exception as e:
                            print(f"Warning: Failed to add category '{new_cat}': {str(e)}")
                
                print(f"Applying categories {category_ids} to generated stories")
                
                # Pass the field data and category_ids to the generate_stories function
                generated_story_ids = story_builder_service.generate_stories(template_id, field_data, category_ids)
                session['generated_story_ids'] = generated_story_ids
                
                if category_ids:
                    flash(f'Stories generated successfully with {len(category_ids)} categories!', 'success')
                else:
                    flash('Stories generated successfully!', 'success')
                    
                return redirect(url_for('main.display_generated_stories'))
            
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print the full error stack
                flash(f'Error generating stories: {str(e)}', 'danger')
                return redirect(url_for('main.generate_stories'))
    
    # GET request - display the form
    templates = story_builder_service.get_all_templates()
    
    # Get template_id either session (by default) or if I've missed something, from the args for backwards compat
    template_id = session.get('template_id') or request.args.get('template_id')

    # Update session if template_id came from query params
    if request.args.get('template_id'):
        session['template_id'] = request.args.get('template_id')
    
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
    
    # Get all categories for the category selection
    categories = category_service.get_all_categories()
    
    return render_template(
        'generate_stories_drag_and_drop.html', 
        templates=templates, 
        selected_template_id=template_id,
        template=template, 
        fields=fields,
        missing_fields=missing_fields,
        categories=categories  
    )

@bp.route('/display_generated_stories', methods=['GET'])
def display_generated_stories():
    # Convert to strings for consistency
    generated_story_ids = [str(story_id) for story_id in session.get('generated_story_ids', [])]
    session['story_ids'] = generated_story_ids
    
    # When querying, convert back to integers
    stories = [db.session.query(Story).get(int(story_id)) for story_id in generated_story_ids]    
    return render_template('display_generated_stories.html', stories=stories)

@bp.route('/add_word', methods=['POST'])
def add_word():
    # Check if this is an AJAX request or a form submission
    is_ajax = request.headers.get('Content-Type') == 'application/json'
    
    if is_ajax:
        # Handle AJAX request (from JavaScript)
        data = request.get_json()
        field_name = data.get('field_name')
        new_words = data.get('new_words')
        
        if field_name and new_words:
            try:
                story_builder_service.add_words_to_field(field_name, new_words)
                return jsonify({'success': True, 'message': f'Word(s) added to {field_name}'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    else:
        # Handle form submission (from HTML form)
        field_name = request.form.get('field_name')
        new_words = request.form.get('new_words')
        template_id = request.form.get('template_id')
        
        if field_name and new_words:
            story_builder_service.add_words_to_field(field_name, new_words)
        
        return redirect(url_for('main.generate_stories', template_id=template_id))

@bp.route('/delete_word', methods=['POST'])
def delete_word():
    data = request.get_json()
    field_name = data.get('field_name')
    word = data.get('word')

    if field_name and word:
        try:
            print(f"Attempting to delete word '{word}' from field '{field_name}'")
            story_builder_service.delete_word_from_field(field_name, word)
            return jsonify({'success': True, 'message': f'Word "{word}" deleted from field "{field_name}".'})
        except Exception as e:
            import traceback
            print(f"ERROR deleting word '{word}' from field '{field_name}':")
            print(traceback.format_exc())  # This prints the full stack trace
            return jsonify({'success': False, 'message': str(e)}), 500
    return jsonify({'success': False, 'message': 'Invalid data provided.'}), 400

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
        # GET request - check for mode parameter
        mode = request.args.get('mode')
        story_ids = session.get('story_ids', [])
        
        # If mode=add or no stories selected, show the selection page
        if mode == 'add' or not story_ids:
            return redirect(url_for('main.see_all_stories'))
        else:
            # Otherwise show the selected stories
            selected_stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
            all_stories = story_service.get_all_stories()
            return render_template('selected_stories.html', selected_stories=selected_stories, all_stories=all_stories)

@bp.route('/select_all_filtered', methods=['POST'])
def select_all_filtered():
    # Check if the request is AJAX
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Invalid request'}), 400
    
    # Get filter parameters from the request
    data = request.get_json()
    search_text = data.get('search_text', '')
    category_filter = data.get('category_filter', '')
    
    # Build the query (similar to see_all_stories but get only IDs)
    query = db.session.query(Story.story_id)
    
    # Apply search filter if provided
    if search_text:
        query = query.filter(Story.content.ilike(f'%{search_text}%'))
    
    # Apply category filter if provided
    if category_filter and category_filter.strip():
        try:
            category_id = int(category_filter)
            query = query.join(StoryCategory).filter(StoryCategory.category_id == category_id)
        except (ValueError, TypeError):
            # Invalid category_filter, ignore it
            pass
    
    # Get all story IDs that match the filters
    story_ids = [str(row.story_id) for row in query.all()]
    
    # Update session with these IDs
    session['story_ids'] = story_ids
    
    # Return the number of stories selected
    return jsonify({
        'success': True,
        'selected_count': len(story_ids),
        'selected_ids': story_ids
    })

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

def run_async_loop():
    global _event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with _event_loop_lock:
        _event_loop = loop  # Thread-safe assignment
    loop.run_forever()

# Helper to get the running event loop (from any thread)
def get_event_loop():
    global _event_loop
    with _event_loop_lock:
        if _event_loop is None:
            raise RuntimeError("Event loop not initialized")
        return _event_loop

# Start the background thread on module load
background_thread = Thread(target=run_async_loop, daemon=True)
background_thread.start()
time.sleep(0.1)  # Small delay to ensure the event loop initializes



# Add job rate limiting to prevent server overload
def can_start_new_job():
    """Check if we can start a new job based on current load"""
    # Count active jobs (those with processing=True and recent activity)
    current_time = time.time()
    active_jobs = 0
    for job in processing_jobs.values():
        if job.get("processing", False) and current_time - job.get("last_activity", 0) < 60:
            active_jobs += 1
    
    # Limit to 5 concurrent jobs (adjust based on your server capacity)
    return active_jobs < 5

# Main processing function that will run in the background asyncio loop
async def process_llm_requests(job_id, model_id, story_ids, question_id, parameters):
    app = create_app()
    with app.app_context():
        job = processing_jobs[job_id]
        job["status"] = "running"
        job["total"] = len(story_ids)
        job["completed"] = 0
        job["results"] = {}
        
        try:
            # Process each story
            for i, story_id in enumerate(story_ids):
                # Check if job has been cancelled
                if job_id not in processing_jobs:
                    return
                
                # Call the LLM service for this story
                story = llm_service.get_story_by_id(story_id)
                question = llm_service.get_question_by_id(question_id)
                provider_name = llm_service.get_provider_name_by_model_id(model_id)
                model_name = llm_service.get_model_name_by_id(model_id)
                
                # Simulate API rate limiting delay
                request_delay = llm_service.get_request_delay_by_model_id(model_id)
                if i > 0 and request_delay > 0:
                    await asyncio.sleep(request_delay)
                
                # Make the actual API call (non-async)
                # We run this in a thread pool since it's a blocking operation
                try:
                    def call_llm_with_context():
                        # This ensures we have an app context in this thread
                        with app.app_context():
                            return llm_service.call_llm(
                                provider_name, 
                                story.content, 
                                question.content, 
                                story_id, 
                                question_id, 
                                model_name, 
                                model_id, 
                                **parameters
                            )

                    loop = asyncio.get_running_loop()
                    # THIS IS THE CRITICAL CHANGE - use the function, not lambda
                    response = await loop.run_in_executor(
                        None,
                        call_llm_with_context
                    )
                    
                    # Update job state
                    job["completed"] += 1
                    if response:
                        # Check if response is a dictionary with response_id
                        if isinstance(response, dict) and "response_id" in response:
                            job["results"][story_id] = {'response_id': response["response_id"]}
                        # Check if response is an object with response_id attribute
                        elif hasattr(response, 'response_id'):
                            job["results"][story_id] = {'response_id': response.response_id}
                        else:
                            print(f"Warning: Unexpected response format: {type(response)}")
                            job["results"][story_id] = {'error': 'Invalid response format'}
                except Exception as e:
                    print(f"Error processing story {story_id}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    job["results"][story_id] = {'error': str(e)}
                
                # Calculate and update progress percentage
                progress = int((job["completed"] / job["total"]) * 100)
                job["progress"] = progress
                job["last_activity"] = time.time()
                
            # Mark job as completed
            job["status"] = "completed"
            job["progress"] = 100
            
            # Keep the results in memory for a few minutes
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            print(f"Error in LLM processing: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Update job with error info
            job["status"] = "error"
            job["error"] = str(e)
            
        finally:
            # Clean up if job still exists
            if job_id in processing_jobs:
                # Don't delete yet, just mark status
                job["processing"] = False


def cleanup_old_jobs():
    """Clean up old jobs that are no longer needed to prevent memory leaks"""
    current_time = time.time()
    jobs_to_remove = []
    
    for job_id, job in processing_jobs.items():
        # Clean up completed jobs older than 30 minutes
        if job.get("status") in ["completed", "error", "cancelled"]:
            if current_time - job.get("last_activity", 0) > 1800:  # 30 minutes
                jobs_to_remove.append(job_id)
        
        # Clean up stalled jobs (no activity for 2 hours)
        elif current_time - job.get("last_activity", 0) > 7200:  # 2 hours
            jobs_to_remove.append(job_id)
    
    # Remove the jobs
    for job_id in jobs_to_remove:
        if job_id in processing_jobs:
            print(f"Cleaning up old job: {job_id}")
            del processing_jobs[job_id]

# Routes for the progress tracking system
@bp.route('/loading')
def loading():
    # Generate unique job ID for this processing request
    job_id = str(uuid.uuid4())
    
    # Extract necessary session data
    model_id = session.get('model_id')
    story_ids = session.get('story_ids', [])
    question_id = session.get('question_id')
    parameters = session.get('parameters', {})
    
    # Store job ID in session
    session['job_id'] = job_id
    
    # Initialize job tracking
    processing_jobs[job_id] = {
        "status": "initializing",
        "progress": 0,
        "total": len(story_ids),
        "completed": 0,
        "results": {},
        "processing": True,
        "last_activity": time.time(),
        # Store parameters for reference
        "params": {
            "model_id": model_id,
            "story_ids": story_ids,
            "question_id": question_id,
            "parameters": parameters
        }
    }
    
    # Clean up old jobs
    cleanup_old_jobs()    
    return render_template('loading.html', job_id=job_id)



# Update start_processing to include rate limiting
@bp.route('/start_processing/<job_id>')
def start_processing(job_id):
    if job_id not in processing_jobs:
        return jsonify({"status": "error", "message": "Invalid job ID"}), 404
    
    job = processing_jobs[job_id]
    
    # Check if we're overloaded
    if not can_start_new_job():
        job["status"] = "queued"
        return jsonify({"status": "queued", "message": "Your job is queued due to high server load"})
    
    params = job["params"]
    
    try:
        # Get the running event loop
        loop = get_event_loop()
        
        # Start processing in background
        task = asyncio.run_coroutine_threadsafe(
            process_llm_requests(
                job_id, 
                params["model_id"], 
                params["story_ids"], 
                params["question_id"], 
                params["parameters"]
            ),
            loop
        )
        
        job["task"] = task
        job["status"] = "started"


        return jsonify({"status": "started"})
    
    except Exception as e:
        print(f"Error starting processing: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update job with error info
        if job_id in processing_jobs:
            processing_jobs[job_id]["status"] = "error"
            processing_jobs[job_id]["error"] = f"Failed to start processing: {str(e)}"
        
        return jsonify({"status": "error", "message": str(e)}), 500
    
@bp.route('/progress_stream/<job_id>')
def progress_stream(job_id):
    print(f"SSE connection requested for job: {job_id}")
    if job_id not in processing_jobs:
        print(f"Job ID not found: {job_id}")
        return jsonify({"status": "error", "message": "Invalid job ID"}), 404
    
    def generate():
        print(f"Starting SSE generator for job: {job_id}")
        last_progress = -1
        timeout = time.time() + 300  # 5 minute maximum wait
        
        # Send an initial message to establish the connection
        initial_data = json.dumps({'status': 'connected', 'job_id': job_id})
        print(f"Sending initial SSE data: {initial_data}")
        yield f"data: {initial_data}\n\n"
        
        try:
            while job_id in processing_jobs:
                job = processing_jobs[job_id]
                current_progress = job.get("progress", 0)
                status = job.get("status", "initializing")
                
                # Update last activity timestamp
                job["last_activity"] = time.time()
                
                # Only send updates when there's a change or status update
                if current_progress != last_progress or status in ["completed", "error", "cancelled"]:
                    last_progress = current_progress
                    
                    # Prepare the response data
                    response_data = {
                        "status": status,
                        "progress": current_progress,
                    }
                    
                    # Add results if completed
                    if status == "completed":
                        results = job.get("results", {})
                        response_ids = [r.get('response_id') for r in results.values() 
                                      if r.get('response_id')]
                        response_data["response_ids"] = response_ids
                        
                        # Store response IDs in the job data instead of the session
                        job["response_ids"] = response_ids
                        
                        # Try to store in session but it will fail outside request context
                        try:
                            # This will fail with "name 'app' is not defined" - that's ok
                            # We'll use job["response_ids"] in the llm_response route
                            session['response_ids'] = response_ids
                        except Exception as e:
                            # If we can't write to session here, that's ok 
                            print(f"Note: Couldn't store response_ids in session: {str(e)}")

                    # Add error info if failed
                    elif status == "error":
                        response_data["error"] = job.get("error", "Unknown error")
                    
                    # Serialize to JSON and send
                    json_data = json.dumps(response_data)
                    print(f"Sending SSE update: {json_data}")
                    yield f"data: {json_data}\n\n"
                    
                    # Break the loop after completion, error, or cancellation
                    if status in ["completed", "error", "cancelled"]:
                        break
                else:
                    # Send a keep-alive comment
                    yield f": keepalive\n\n"  # Changed to just keepalive without timestamp
                
                # Check for timeout
                if time.time() > timeout:
                    timeout_data = json.dumps({'status': 'timeout', 'progress': current_progress})
                    print(f"SSE timeout: {timeout_data}")
                    yield f"data: {timeout_data}\n\n"
                    break
                    
                # Wait a bit before next update
                time.sleep(0.5)
        except Exception as e:
            print(f"Error in SSE stream: {str(e)}")
            import traceback
            traceback.print_exc()
            # Send an error message if something goes wrong
            error_data = json.dumps({'status': 'error', 'error': str(e)})
            print(f"SSE error: {error_data}")
            yield f"data: {error_data}\n\n"
    
    # Set the appropriate headers for SSE
    response = FlaskResponse(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@bp.route('/cancel_processing/<job_id>')
def cancel_processing(job_id):
    if job_id in processing_jobs:
        # Mark job as cancelled
        processing_jobs[job_id]["status"] = "cancelled"
        processing_jobs[job_id]["processing"] = False
        
        # Clean up after a short delay
        def delayed_cleanup():
            time.sleep(5)
            if job_id in processing_jobs:
                del processing_jobs[job_id]
        
        Thread(target=delayed_cleanup, daemon=True).start()
        
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "error", "message": "Job not found"}), 404

#possibly not needed now
@bp.route('/progress')
def progress_legacy():
    job_id = session.get('job_id')
    if not job_id or job_id not in processing_jobs:
        return jsonify({"error": "No active job found"}), 404
    
    # Redirect to the new progress stream
    return redirect(url_for('main.progress_stream', job_id=job_id))

@bp.route('/llm_response', methods=['GET', 'POST'])
def llm_response():
    if request.method == 'POST':
        print("POST request received on llm_response")
        # Process form data
        response_id = request.form.get('response_id')
        print(f"Response ID from form: {response_id}")
        
        if response_id:
            flagged_for_review = f'flagged_for_review_{response_id}' in request.form
            review_notes = request.form.get(f'review_notes_{response_id}', '')
            
            print(f"Flagged for review: {flagged_for_review}")
            print(f"Review notes: {review_notes}")

            try:
                # Get the response
                response = db.session.query(Response).get(response_id)
                if response:
                    print(f"Found response {response_id} in database")
                    # Update the fields
                    response.flagged_for_review = flagged_for_review
                    response.review_notes = review_notes
                    
                    # Simpler transaction handling - just commit the change
                    db.session.commit()
                    
                    print(f"Successfully updated response {response_id}")
                    flash(f'Response {response_id} updated successfully!', 'success')
                else:
                    print(f"Response {response_id} not found in database")
                    flash(f'Error: Response {response_id} not found.', 'danger')
            except Exception as e:
                print(f"Error updating response: {str(e)}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                flash(f'Error updating response: {str(e)}', 'danger')

        return redirect(url_for('main.llm_response'))

    # Get job_id from the session
    job_id = session.get('job_id')
    
    # Try to get response_ids from the job data first
    response_ids = []
    if job_id and job_id in processing_jobs:
        # Get from job data
        job = processing_jobs[job_id]
        response_ids = job.get("response_ids", [])
        
        # If we found response IDs, store them in the session for future use
        # (especially after the job is cleaned up)
        if response_ids:
            session['response_ids'] = response_ids
    
    # If no response_ids found in job data, try session as fallback
    if not response_ids:
        response_ids = session.get('response_ids', [])
    
    print(f"Retrieved response_ids: {response_ids}")
    
    # Fetch stories
    story_ids = session.get('story_ids', [])
    stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
    
    # Fetch responses
    responses = []
    for response_id in response_ids:
        response = db.session.query(Response).get(response_id)
        if response:
            responses.append(response)
    
    print(f"Found {len(responses)} responses")
    
    # If we have no responses but have story_ids, perhaps the responses weren't stored properly
    if not responses and story_ids:
        flash('No responses found for your stories. There might have been an issue with the LLM processing.', 'warning')
    
    response_details = []
    for response in responses:
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

@bp.route('/view_responses', methods=['GET', 'POST'])
def view_responses():
    if request.method == 'POST':
        # Process form data for response updates
        response_id = request.form.get('response_id')
        
        if response_id:
            # Check if the response exists
            response = db.session.query(Response).get(response_id)
            if response:
                # Update flag status - checked boxes return 'on', unchecked return None
                flagged_for_review = f'flagged_for_review_{response_id}' in request.form
                review_notes = request.form.get(f'review_notes_{response_id}', '')
                
                # Apply changes
                response.flagged_for_review = flagged_for_review
                response.review_notes = review_notes
                db.session.commit()
                
                flash('Response updated successfully!', 'success')
            else:
                flash('Error: Response not found.', 'danger')
                
        # Redirect back to the same page (with filters preserved)
        return redirect(url_for('main.view_responses', **request.args))
    
 # GET request - handle filtering
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    flagged_only = 'flagged_only' in request.args
    question_id = request.args.get('question_id', '')
    story_id = request.args.get('story_id', '')
    
    # Date range filtering
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Sorting option
    sort = request.args.get('sort', 'date_desc')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with the existing joins
    query = db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Model, Prompt.model_id == Model.model_id).\
        join(Provider, Model.provider_id == Provider.provider_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        join(Question, Prompt.question_id == Question.question_id)
    
    # Apply regular filters
    if provider:
        query = query.filter(Provider.provider_name.ilike(f'%{provider}%'))
    if model:
        query = query.filter(Model.name.ilike(f'%{model}%'))
    if flagged_only:
        query = query.filter(Response.flagged_for_review == True)
    if question_id:
        query = query.filter(Prompt.question_id == question_id)
    if story_id:
        query = query.filter(Prompt.story_id == story_id)
    
    # Apply date range filters
    if start_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Response.timestamp >= start_date_obj)
        except ValueError:
            flash(f"Invalid start date format: {start_date}", "warning")
    
    if end_date:
        try:
            # Add one day to include the end date fully
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            query = query.filter(Response.timestamp < end_date_obj)
        except ValueError:
            flash(f"Invalid end date format: {end_date}", "warning")
    
    # Apply sorting
    if sort == 'date_asc':
        query = query.order_by(Response.timestamp.asc())
    else:  # Default to date_desc
        query = query.order_by(Response.timestamp.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    responses = pagination.items
    
    # Get data for filter dropdowns
    providers = db.session.query(Provider).all()
    models = db.session.query(Model).all()
    questions = db.session.query(Question).all()
    
    return render_template('see_all_responses.html', 
                          responses=responses,
                          pagination=pagination,
                          providers=providers,
                          models=models,
                          questions=questions,
                          current_filters={
                              'provider': provider,
                              'model': model,
                              'flagged_only': flagged_only,
                              'question_id': question_id,
                              'story_id': story_id,
                              'start_date': start_date,
                              'end_date': end_date,
                              'sort': sort
                          })

@bp.route('/update_response_flag', methods=['POST'])
def update_response_flag():
    """AJAX endpoint to quickly toggle a response's flag status"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    data = request.get_json()
    response_id = data.get('response_id')
    flagged = data.get('flagged', False)
    
    try:
        response = db.session.query(Response).get(response_id)
        if not response:
            return jsonify({'success': False, 'message': 'Response not found'}), 404
        
        response.flagged_for_review = flagged
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response_id': response_id,
            'flagged': response.flagged_for_review
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    


@bp.route('/export_responses', methods=['GET'])
def export_responses():
    # Get the same filters you use in view_responses
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    # ...other filters...
    
    # Build and execute the query (same as in view_responses but without pagination)
    query = db.session.query(Response)
    # ...apply the same filters...
    
    # Get all matching responses
    responses = query.all()
    
    # Create a memory file for the CSV data
    mem_file = io.StringIO()
    csv_writer = csv.writer(mem_file, quoting=csv.QUOTE_MINIMAL)
    
    # Write header row
    csv_writer.writerow(['ID', 'Date', 'Time', 'Provider', 'Model', 
                         'Temperature', 'Max Tokens', 'Top P',
                         'Story ID', 'Story', 'Question ID', 'Question', 
                         'Response', 'Flagged', 'Review Notes'])
    
    # Write data rows
    for response in responses:
        csv_writer.writerow([
            response.response_id,
            response.timestamp.strftime('%d/%m/%Y'),
            response.timestamp.strftime('%H:%M'),
            response.prompt.model.provider.provider_name,
            response.prompt.model.name,
            response.prompt.temperature,
            response.prompt.max_tokens,
            response.prompt.top_p,
            response.prompt.story_id,
            response.prompt.story.content,
            response.prompt.question_id,
            response.prompt.question.content,
            response.response_content,
            'Yes' if response.flagged_for_review else 'No',
            response.review_notes or ''
        ])
    
    # Move cursor to beginning of file
    mem_file.seek(0)
    
    # Add an export button to your template
    return send_file(
        io.BytesIO(mem_file.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'responses_export_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
    )


@bp.route('/clear_session', methods=['GET'])
def clear_session():
    print("Session before clearing:")
    print(session)
    print("Clearing session and canceling background tasks")
    
    # Cancel and clean up any ongoing processing jobs
    cleared_jobs = 0
    for job_id, job in list(processing_jobs.items()):
        try:
            # Cancel the task if it exists and is not done
            if "task" in job and hasattr(job["task"], "cancel") and not job["task"].done():
                print(f"Canceling task for job {job_id}")
                job["task"].cancel()
                cleared_jobs += 1
            
            # Mark job as cancelled
            job["status"] = "cancelled"
            job["processing"] = False
        except Exception as e:
            print(f"Error canceling job {job_id}: {str(e)}")
    
    # Clear all processing jobs
    processing_jobs.clear()
    
    # Clear session data
    session.clear()
    
    flash(f'Session data cleared and {cleared_jobs} background tasks cancelled!', 'success')
    print("Session after clearing:", session)
    print(f"Cleared {cleared_jobs} tasks from processing_jobs")
    
    return redirect(url_for('main.index'))