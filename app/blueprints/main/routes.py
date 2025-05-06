import datetime
from flask import Blueprint, flash, render_template, request, redirect, url_for, session, jsonify, Response as FlaskResponse, send_file

from app.services import async_service
from ... import db, create_app
from ...services import story_service, question_service, story_builder_service, llm_service, category_service
from ...models import Template, Story, Question, Model, Provider, Response, StoryCategory, Prompt, Field
import time
import json
import threading
from threading import Thread
import asyncio
import uuid
import csv
import io
from . import main_bp

#Another silly change to check new branchv2

# Create a blueprint for the routes

processing_jobs = {}
_event_loop = None
_event_loop_lock = threading.Lock()

@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/clear_session', methods=['GET'])
def clear_session():

    # Get selective clearing parameters
    clear_model = request.args.get('clear_model') == 'true'
    clear_parameters = request.args.get('clear_parameters') == 'true'
    clear_stories = request.args.get('clear_stories') == 'true'
    clear_question = request.args.get('clear_question') == 'true'
    clear_all = 'clear_all' in request.args
    
    print("Session before clearing:", dict(session))
    
    if clear_all:
        # Current behavior - full clearing and job cancellation
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
        print(f"Cleared {cleared_jobs} tasks from processing_jobs")
    else:
        # Selective clearing of session data
        items_cleared = []
        stories_source = request.args.get('stories_source') == 'true'
        clear_templates = request.args.get('clear_templates') == 'true'

        if stories_source and 'stories_source' in session:
            session.pop('stories_source')
            session.pop('template_count', None)  # Also clear template_count
            items_cleared.append('template filter')

        if clear_templates and 'template_ids' in session:
            session.pop('template_ids')
            items_cleared.append('template selection')
        # Clear model and provider if requested
        if clear_model:
            model_cleared = False
            if 'model' in session:
                session.pop('model')
                model_cleared = True
            if 'provider' in session:
                session.pop('provider')
                model_cleared = True
            if 'model_id' in session:
                session.pop('model_id')
                model_cleared = True
            
            if model_cleared:
                items_cleared.append('model selection')
        
        if clear_parameters and 'parameters' in session:
            session.pop('parameters')
            items_cleared.append('parameters')
            
        if clear_stories and 'story_ids' in session:
            session.pop('story_ids')
            items_cleared.append('story selection')
            
        if clear_question and 'question_id' in session:
            session.pop('question_id')
        if 'question_content' in session:
            session.pop('question_content')
            items_cleared.append('question')
            
        # Only show a flash message if something was cleared
        if items_cleared:
            flash(f'Cleared {", ".join(items_cleared)} from session', 'info')
        
       

        print("Session after selective clearing:", dict(session))
    
    # Get the redirect URL - either specified or default to index
    redirect_url = request.args.get('redirect_to', url_for('main.index'))
    return redirect(redirect_url)
   







# def run_async_loop():
#     global _event_loop
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     with _event_loop_lock:
#         _event_loop = loop  # Thread-safe assignment
#     loop.run_forever()

# # Helper to get the running event loop (from any thread)
# def get_event_loop():
#     global _event_loop
#     with _event_loop_lock:
#         if _event_loop is None:
#             raise RuntimeError("Event loop not initialized")
#         return _event_loop

# # Start the background thread on module load
# background_thread = Thread(target=run_async_loop, daemon=True)
# background_thread.start()
# time.sleep(0.1)  # Small delay to ensure the event loop initializes


@main_bp.route('/view_responses', methods=['GET', 'POST'])
def view_responses():
    # Handle POST requests as before
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        if response_id:
            try:
                # Get the response object
                response = db.session.query(Response).get(response_id)
                if response:
                    # Update flagged status
                    flagged_key = f'flagged_for_review_{response_id}'
                    response.flagged_for_review = flagged_key in request.form
                    
                    # Update review notes
                    notes_key = f'review_notes_{response_id}'
                    response.review_notes = request.form.get(notes_key, '')
                    
                    # Commit changes
                    db.session.commit()
                    flash(f'Response {response_id} updated successfully!', 'success')
                else:
                    flash(f'Error: Response {response_id} not found.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating response: {str(e)}', 'danger')
                
        # Redirect back to the same page with all arguments preserved
        return redirect(url_for('main.view_responses', **request.args))
        
    
    # Clear flags processing
    if 'clear_stories' in request.args and 'story_ids' in session:
        session.pop('story_ids')
        
    if 'clear_responses' in request.args and 'response_ids' in session:
        session.pop('response_ids')
    
    if 'clear_templates' in request.args and 'template_ids' in session:
        session.pop('template_ids')

    # Build the base query
    query = db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Model, Prompt.model_id == Model.model_id).\
        join(Provider, Model.provider_id == Provider.provider_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        join(Question, Prompt.question_id == Question.question_id)
    
    # Get all filter parameters
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    flagged_only = 'flagged_only' in request.args
    question_id = request.args.get('question_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')   
    
    # SOURCE-based filtering (primary selection)
    source = request.args.get('source', '')
    source_id = None
    source_info = None
    
    # Apply source-based filtering
    response_ids = session.get('response_ids', [])
    if response_ids and 'clear_responses' not in request.args:
        # Filter by specific responses (from prompt or story)
        int_response_ids = [int(rid) for rid in response_ids]
        query = query.filter(Response.response_id.in_(int_response_ids))
        
        # Handle source information for display
        if source == 'prompt':
            prompt_id = request.args.get('prompt_id')
            if prompt_id:
                source_id = prompt_id
                prompt = db.session.query(Prompt).get(int(prompt_id))
                if prompt:
                    source_info = f"Prompt #{prompt_id} ({prompt.model.name})"
        elif source == 'story':
            story_count = request.args.get('story_count', '1')
            story_id_param = request.args.get('story_id')
            
            if story_count and int(story_count) > 1:
                source_info = f"{story_count} Selected Stories"
            elif story_id_param:
                source_id = story_id_param
                story = db.session.query(Story).get(int(story_id_param))
                if story:
                    content_preview = story.content[:50] + '...' if len(story.content) > 50 else story.content
                    source_info = f"Story #{story_id_param} ({content_preview})"
        elif source == 'template':
            template_count = request.args.get('template_count', '1')
            template_id_param = request.args.get('template_id')
            
            if template_count and int(template_count) > 1:
                source_info = f"{template_count} Selected Templates"
            elif template_id_param:
                source_id = template_id_param
                template = db.session.query(Template).get(int(template_id_param))
                if template:
                    content_preview = template.content[:50] + '...' if len(template.content) > 50 else template.content
                    source_info = f"Template #{template_id_param} ({content_preview})"
    # Otherwise check for story_ids in session (multiple stories selected)
    elif session.get('story_ids') and 'clear_stories' not in request.args:
        story_ids = [int(sid) for sid in session.get('story_ids', [])]
        query = query.filter(Prompt.story_id.in_(story_ids))
    # Add this check for template_ids in session
    elif session.get('template_ids') and 'clear_templates' not in request.args:
        template_ids = [int(tid) for tid in session.get('template_ids', [])]
        # First, get stories that use these templates
        story_subquery = db.session.query(Story.story_id).filter(Story.template_id.in_(template_ids))
        # Then filter prompts by those stories
        query = query.filter(Prompt.story_id.in_(story_subquery))
        # Set source info for display
        template_count = len(template_ids)
        if template_count == 1:
            template = db.session.query(Template).get(template_ids[0])
            if template:
                content_preview = template.content[:50] + '...' if len(template.content) > 50 else template.content
                source_info = f"Template #{template_ids[0]} ({content_preview})"
            else:
                source_info = f"Template #{template_ids[0]}"
        else:
            source_info = f"{template_count} Selected Templates"
    # SECONDARY FILTERING - Always apply regardless of source selection
    if provider:
        query = query.filter(Provider.provider_name.ilike(f'%{provider}%'))
    if model:
        query = query.filter(Model.name.ilike(f'%{model}%'))
    if flagged_only:
        query = query.filter(Response.flagged_for_review.is_(True))
    if question_id:
        query = query.filter(Prompt.question_id == question_id)
    
    # Apply date filtering
    if start_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Response.timestamp >= start_date_obj)
        except ValueError:
            flash(f"Invalid start date format: {start_date}", "warning")
    
    if end_date:
        try:
            # Add 1 day to include the end date fully
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            query = query.filter(Response.timestamp < end_date_obj)
        except ValueError:
            flash(f"Invalid end date format: {end_date}", "warning")
    
    # Apply sorting
    if sort == 'date_asc':
        query = query.order_by(Response.timestamp.asc())
    else:  # Default to date_desc
        query = query.order_by(Response.timestamp.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of responses per page
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    responses = pagination.items  
    
    # Get data for filter dropdowns
    providers = db.session.query(Provider).all()
    models = db.session.query(Model).all()
    questions = db.session.query(Question).all()
    
    # Track if we're filtering by specific responses
    has_response_filter = bool(response_ids and 'clear_responses' not in request.args)
    
    # Track if we have secondary filter criteria applied
    has_secondary_filters = any([provider, model, flagged_only, question_id, start_date, end_date])
    
    return render_template('see_all_responses.html', 
                          responses=responses,
                          pagination=pagination,
                          providers=providers,
                          models=models,
                          questions=questions,
                          has_response_filter=has_response_filter,
                          has_secondary_filters=has_secondary_filters,
                          source=source,
                          source_id=source_id,
                          source_info=source_info,
                          current_filters={
                              'provider': provider,
                              'model': model,
                              'flagged_only': flagged_only,
                              'question_id': question_id,
                              'story_id': request.args.get('story_id', ''),
                              'start_date': start_date,
                              'end_date': end_date,
                              'sort': sort
                          })
    

@main_bp.route('/update_response_flag', methods=['POST'])
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
    
@main_bp.route('/export_responses', methods=['GET'])
def export_responses():
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    flagged_only = 'flagged_only' in request.args
    question_id = request.args.get('question_id', '')
    story_id = request.args.get('story_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')
    
    # Build query with the existing joins - EXACTLY as in view_responses
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
    
    # Apply sorting - though it doesn't matter much for export
    if sort == 'date_asc':
        query = query.order_by(Response.timestamp.asc())
    else:  # Default to date_desc
        query = query.order_by(Response.timestamp.desc())
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


@main_bp.route('/see_all_prompts', methods=['GET', 'POST'])
def see_all_prompts():
    if request.method == 'POST':
        # Process form data for prompt updates if needed
        # (Similar to view_responses POST handler but for prompts)
        return redirect(url_for('main.see_all_prompts', **request.args))
        
    # Initialize prompt_ids for selection
    selected_prompt_ids = session.get('prompt_ids', [])
    
    # GET request - handle filtering
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    question_id = request.args.get('question_id', '')
    story_id = request.args.get('story_id', '')
    
    # Date range filtering
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Sorting option
    sort = request.args.get('sort', 'date_desc')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with joins
    query = db.session.query(
        Prompt, 
        db.func.max(Response.timestamp).label('last_used')
    ).\
        join(Model, Prompt.model_id == Model.model_id).\
        join(Provider, Model.provider_id == Provider.provider_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        join(Question, Prompt.question_id == Question.question_id).\
        outerjoin(Response, Prompt.prompt_id == Response.prompt_id).\
        group_by(Prompt.prompt_id)
    
    # Apply regular filters
    if provider:
        query = query.filter(Provider.provider_name.ilike(f'%{provider}%'))
    if model:
        query = query.filter(Model.name.ilike(f'%{model}%'))
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
        query = query.order_by(db.func.max(Response.timestamp).asc())
    else:  # Default to date_desc
        query = query.order_by(db.func.max(Response.timestamp).desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    prompt_data = pagination.items
    
    # Get data for filter dropdowns
    providers = db.session.query(Provider).all()
    models = db.session.query(Model).all()
    questions = db.session.query(Question).all()
    
    return render_template('see_all_prompts.html', 
                          prompts=prompt_data,
                          pagination=pagination,
                          providers=providers,
                          models=models,
                          questions=questions,
                          selected_prompt_ids=selected_prompt_ids,
                          current_filters={
                              'provider': provider,
                              'model': model,
                              'question_id': question_id,
                              'story_id': story_id,
                              'start_date': start_date,
                              'end_date': end_date,
                              'sort': sort
                          })

@main_bp.route('/update_prompt_selection', methods=['POST'])
def update_prompt_selection():
    data = request.get_json()
    
    # Get the current selection from session
    selected_prompt_ids = session.get('prompt_ids', [])
    
    # Clear all selected prompts
    if data.get('action') == 'clear_all':
        selected_prompt_ids = []
    
    # Select multiple prompts at once
    elif data.get('action') == 'select_multiple':
        prompt_ids = data.get('prompt_ids', [])
        for prompt_id in prompt_ids:
            if prompt_id not in selected_prompt_ids:
                selected_prompt_ids.append(prompt_id)
    
    # Invert selection
    elif data.get('action') == 'invert_selection':
        select_ids = data.get('select_ids', [])
        deselect_ids = data.get('deselect_ids', [])
        
        # Add new selections
        for pid in select_ids:
            if pid not in selected_prompt_ids:
                selected_prompt_ids.append(pid)
                
        # Remove deselections
        selected_prompt_ids = [pid for pid in selected_prompt_ids if pid not in deselect_ids]
    """AJAX endpoint to update prompt selection in session"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    data = request.get_json()
    
    # Get the current selection from session
    selected_prompt_ids = session.get('prompt_ids', [])
    
    # Clear all selected prompts
    if data.get('action') == 'clear_all':
        selected_prompt_ids = []
    
    # Select multiple prompts at once (for batch operations)
    elif data.get('action') == 'select_multiple':
        prompt_ids = data.get('prompt_ids', [])
        for prompt_id in prompt_ids:
            if prompt_id not in selected_prompt_ids:
                selected_prompt_ids.append(prompt_id)
    
    # Handle individual toggle
    elif 'prompt_id' in data:
        prompt_id = str(data['prompt_id'])
        is_selected = data.get('selected', False)
        
        if is_selected and prompt_id not in selected_prompt_ids:
            selected_prompt_ids.append(prompt_id)
        elif not is_selected and prompt_id in selected_prompt_ids:
            selected_prompt_ids.remove(prompt_id)
    
    # Store updated selection in session
    session['prompt_ids'] = selected_prompt_ids
    
    return jsonify({
        'success': True,
        'selected_count': len(selected_prompt_ids),
        'selected_ids': selected_prompt_ids
    })

@main_bp.route('/view_prompt_responses/<int:prompt_id>')
def view_prompt_responses(prompt_id):
    """View all responses for a specific prompt"""
    # Get all responses for this prompt
    responses = db.session.query(Response).filter(Response.prompt_id == prompt_id).all()
    
    if not responses:
        flash(f'No responses found for prompt ID {prompt_id}', 'info')
        return redirect(url_for('main.see_all_prompts'))
    
    # Clear any existing response filters first
    if 'response_ids' in session:
        session.pop('response_ids')
    
    # Store response IDs as strings in session
    session['response_ids'] = [str(r.response_id) for r in responses]
    
    # Add a query parameter to indicate source
    return redirect(url_for('main.view_responses', source='prompt', prompt_id=prompt_id))

@main_bp.route('/view_story_responses')
def view_story_responses():
    """View all responses related to stories selected in session"""
    
    # Get story IDs from session
    story_ids = session.get('story_ids', [])
    
    if not story_ids:
        flash('No stories selected. Please select at least one story.', 'warning')
        return redirect(url_for('stories.list'))
    
    # Convert story IDs to integers for the database query
    int_story_ids = [int(sid) for sid in story_ids]
    
    # Get all responses for these stories
    responses = db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        filter(Prompt.story_id.in_(int_story_ids)).all()
    
    if not responses:
        flash('No responses found for the selected stories', 'info')
        return redirect(url_for('stories.list'))
    
    # Clear any existing response filters first
    if 'response_ids' in session:
        session.pop('response_ids')
    
    # Store response IDs as strings in session
    session['response_ids'] = [str(r.response_id) for r in responses]
    
    # Generate appropriate message based on count
    story_count = len(story_ids)
  
    
    # Use a single redirect approach
    return redirect(url_for('main.view_responses', 
                           source='story', 
                           story_count=story_count,
                           story_id=int_story_ids[0] if story_count == 1 else None))

@main_bp.route('/view_template_responses')
def view_template_responses():
    """View all responses related to templates selected in session"""
    
    # Get template IDs from session
    template_ids = session.get('template_ids', [])
    
    if not template_ids:
        flash('No templates selected. Please select at least one template.', 'warning')
        return redirect(url_for('main.see_all_templates'))
    
    # Convert template IDs to integers for the database query
    int_template_ids = [int(tid) for tid in template_ids]
    
    # Get all responses for these templates
    responses = db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        filter(Story.template_id.in_(int_template_ids)).all()
    
    if not responses:
        flash('No responses found for the selected templates', 'info')
        return redirect(url_for('main.see_all_templates'))
    
    # Clear any existing response filters first
    if 'response_ids' in session:
        session.pop('response_ids')
    
    # Store response IDs as strings in session
    session['response_ids'] = [str(r.response_id) for r in responses]
    
    # Generate appropriate message based on count
    template_count = len(template_ids)
    
    #Content for info message in green box at top of Response Database
    if template_count == 1:
            # Get the template content for a single template
            template = db.session.query(Template).get(int_template_ids[0])
            if template:
                content_preview = (template.content[:40] + '...') if len(template.content) > 40 else template.content
                source_info = f"Template #{int_template_ids[0]} ({content_preview})"
            else:
                source_info = f"Template #{int_template_ids[0]}"
    else:
            # For multiple templates, show the count
        source_info = f"{template_count} Selected Templates"

    # Use a single redirect approach
    return redirect(url_for('main.view_responses', 
                           source='template',
                           source_info = source_info, 
                           template_count=template_count,
                           template_id=int_template_ids[0] if template_count == 1 else None))

