import csv

#previously view_resoponses
import datetime
import io

from flask import (
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask import Response as FlaskResponse

from ... import db
from ...models import Model, Prompt, Provider, Question, Response, Story, Template
from ...services import async_service, response_service
from . import responses_bp


@responses_bp.route('/list', methods=['GET', 'POST'])
def list():
    # Handle POST requests for updating responses
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        if response_id:
            # Update flagged status
            flagged_key = f'flagged_for_review_{response_id}'
            flagged_for_review = flagged_key in request.form
            
            # Update review notes
            notes_key = f'review_notes_{response_id}'
            review_notes = request.form.get(notes_key, '')
            
            success, error = response_service.update_response_review(
                response_id, 
                flagged_for_review, 
                review_notes
            )
            
            if success:
                flash(f'Response {response_id} updated successfully!', 'success')
            else:
                flash(f'Error updating response: {error}', 'danger')
                
        # Redirect back to the same page with all arguments preserved
        return redirect(url_for('responses.list', **request.args))
    
    # Clear flags processing
    if 'clear_stories' in request.args and 'story_ids' in session:
        session.pop('story_ids')
        
    if 'clear_responses' in request.args and 'response_ids' in session:
        session.pop('response_ids')
    
    if 'clear_templates' in request.args and 'template_ids' in session:
        session.pop('template_ids')
    if 'clear_prompts' in request.args and 'prompt_ids' in session:
        session.pop('prompt_ids')
    
     # Get all filter parameters
    run_id = request.args.get('run_id', '')
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    flagged_only = bool(request.args.get('flagged_only'))
    question_id = request.args.get('question_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')   

    # If a run is selected, override provider/model/question_id with those from the run
    if run_id:
        run_provider, run_model, run_question_id = response_service.get_filters_for_run(run_id)
        if run_provider:
            provider = run_provider
        if run_model:
            model = run_model
        if run_question_id:
            question_id = str(run_question_id)

    # ...rest of your logic unchanged...
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config["PER_PAGE"], type=int)
    source = request.args.get('source', '')
    source_id = request.args.get('source_id') or request.args.get('prompt_id') or request.args.get('story_id') or request.args.get('template_id')
    source_count = request.args.get('story_count') or request.args.get('template_count')

    filter_kwargs = {
        'provider': provider,
        'model': model,
        'flagged_only': flagged_only,
        'question_id': question_id,
        'start_date': start_date,
        'end_date': end_date,
        'sort': sort
    }
    if run_id:
        filter_kwargs['run_id'] = run_id

    # # Get all filter parameters
    # provider = request.args.get('provider', '')
    # model = request.args.get('model', '')
    # flagged_only = bool(request.args.get('flagged_only'))
    # question_id = request.args.get('question_id', '')
    # start_date = request.args.get('start_date', '')
    # end_date = request.args.get('end_date', '')
    # sort = request.args.get('sort', 'date_desc')   
    
    # # Get pagination parameters
    # page = request.args.get('page', 1, type=int)
    # per_page = request.args.get('per_page', current_app.config["PER_PAGE"], type=int)
    
    # # SOURCE-based filtering (primary selection)
    # source = request.args.get('source', '')
    # source_id = request.args.get('source_id') or request.args.get('prompt_id') or request.args.get('story_id') or request.args.get('template_id')
    # source_count = request.args.get('story_count') or request.args.get('template_count')
    
    # # Determine which filter should be applied
    # filter_kwargs = {
    #     'provider': provider,
    #     'model': model,
    #     'flagged_only': flagged_only,
    #     'question_id': question_id,
    #     'start_date': start_date,
    #     'end_date': end_date,
    #     'sort': sort
    # }
    
    # Add source-specific filters
    response_ids = session.get('response_ids', [])
    if response_ids and 'clear_responses' not in request.args:
        filter_kwargs['response_ids'] = response_ids
    elif session.get('story_ids') and 'clear_stories' not in request.args:
        filter_kwargs['story_ids'] = session.get('story_ids')
    elif session.get('template_ids') and 'clear_templates' not in request.args:
        filter_kwargs['template_ids'] = session.get('template_ids')
    
    # Get paginated responses
    pagination = response_service.get_responses_paginated(
        page=page,
        per_page=per_page,
        **filter_kwargs
    )
    
    # Get filter options for dropdowns
    filter_options = response_service.get_filter_options()
    
    # Get source information for display
    source_info = response_service.get_source_info(source, source_id, source_count)
    
    # Track if we're filtering by specific responses or have secondary filters
    has_response_filter = bool(response_ids and 'clear_responses' not in request.args)
    has_secondary_filters = any([provider, model, flagged_only, question_id, start_date, end_date])
    runs = response_service.get_all_runs()

    return render_template('see_all_responses.html', 
                          responses=pagination.items,
                          pagination=pagination,
                          providers=filter_options['providers'],
                          models=filter_options['models'],
                          questions=filter_options['questions'],
                          has_response_filter=has_response_filter,
                          has_secondary_filters=has_secondary_filters,
                          source=source,
                          source_id=source_id,
                          source_info=source_info,
                          current_filters={
                              'run_id': run_id,
                              'provider': provider,
                              'model': model,
                              'flagged_only': flagged_only,
                              'question_id': question_id,
                              'story_id': request.args.get('story_id', ''),
                              'start_date': start_date,
                              'end_date': end_date,
                              'sort': sort
                        
                          },
                          runs = runs
                          
                          )
    
    # return render_template('see_all_responses.html', 
    #                       responses=pagination.items,
    #                       pagination=pagination,
    #                       providers=filter_options['providers'],
    #                       models=filter_options['models'],
    #                       questions=filter_options['questions'],
    #                       has_response_filter=has_response_filter,
    #                       has_secondary_filters=has_secondary_filters,
    #                       source=source,
    #                       source_id=source_id,
    #                       source_info=source_info,
    #                       current_filters={
    #                           'provider': provider,
    #                           'model': model,
    #                           'flagged_only': flagged_only,
    #                           'question_id': question_id,
    #                           'story_id': request.args.get('story_id', ''),
    #                           'start_date': start_date,
    #                           'end_date': end_date,
    #                           'sort': sort
    #                       })

@responses_bp.route('/update_response_flag', methods=['POST'])
def update_response_flag():
    """AJAX endpoint to quickly toggle a response's flag status - without reloading the page"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    data = request.get_json()
    response_id = data.get('response_id')
    flagged = data.get('flagged', False)
    
    success, error = response_service.update_response_flag(response_id, flagged)
    
    if success:
        return jsonify({
            'success': True,
            'response_id': response_id,
            'flagged': flagged
        })
    else:
        return jsonify({'success': False, 'message': error}), 500

@responses_bp.route('/export', methods=['GET'])
def export():
    # Get all filter parameters
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    flagged_only = 'flagged_only' in request.args
    question_id = request.args.get('question_id', '')
    story_id = request.args.get('story_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')
    
    # Construct filter parameters
    filter_kwargs = {
        'provider': provider,
        'model': model,
        'flagged_only': flagged_only,
        'question_id': question_id,
        'story_id': story_id,
        'start_date': start_date,
        'end_date': end_date,
        'sort': sort
    }
    
    # Add source-specific filters
    response_ids = session.get('response_ids', [])
    if response_ids:
        filter_kwargs['response_ids'] = response_ids
    elif session.get('story_ids'):
        filter_kwargs['story_ids'] = session.get('story_ids')
    elif session.get('template_ids'):
        filter_kwargs['template_ids'] = session.get('template_ids')
    
    # Build query and get all responses (no pagination needed for export)
    stmt = response_service.build_response_query(**filter_kwargs)
    responses = db.session.execute(stmt).scalars().all()
    
    # Generate CSV file
    csv_data = response_service.generate_csv_export(responses)
    
    # Send file
    return send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'responses_export_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
    )

# @responses_bp.route('/view_prompt_responses/<int:prompt_id>')
# def view_prompt_responses(prompt_id):
#     """View all responses for a specific prompt"""
#     # Get all responses for this prompt
#     responses = response_service.get_responses_for_prompt(prompt_id)
    
#     if not responses:
#         flash(f'No responses found for prompt ID {prompt_id}', 'info')
#         return redirect(url_for('prompts.list'))
    
#     # Clear any existing response filters first
#     if 'response_ids' in session:
#         session.pop('response_ids')
    
#     # Store response IDs as strings in session
#     session['response_ids'] = [str(r.response_id) for r in responses]
    
#     # Add a query parameter to indicate source
#     return redirect(url_for('responses.list', source='prompt', prompt_id=prompt_id))


# @responses_bp.route('/view_prompt_responses_batch')
# def view_prompt_responses_batch():
#     """View all responses for the selected prompts in session"""
#     # Get prompt IDs from session
#     prompt_ids = session.get('prompt_ids', [])
    
#     if not prompt_ids:
#         flash('No prompts selected. Please select at least one prompt.', 'warning')
#         return redirect(url_for('prompts.list'))
    
#     # Get all responses for these prompts
#     responses = []
#     for prompt_id in prompt_ids:
#         prompt_responses = response_service.get_responses_for_prompt(int(prompt_id))
#         responses.extend(prompt_responses)
    
#     if not responses:
#         flash('No responses found for the selected prompts', 'info')
#         return redirect(url_for('prompts.list'))
    
#     # Clear any existing response filters first
#     if 'response_ids' in session:
#         session.pop('response_ids')
    
#     # Store response IDs as strings in session
#     session['response_ids'] = [str(r.response_id) for r in responses]
    
#     # Use a redirect approach with appropriate source info
#     return redirect(url_for('responses.list', 
#                            source='prompt_batch', 
#                            prompt_count=len(prompt_ids)))

@responses_bp.route('/view_prompt_responses')
def view_prompt_responses():
    """View all responses for the selected prompts in session"""
    prompt_ids = session.get('prompt_ids', [])
    # If only one prompt_id, allow for int or str
    if isinstance(prompt_ids, (str, int)):
        prompt_ids = [prompt_ids]
    if not prompt_ids:
        flash('No prompts selected. Please select at least one prompt.', 'warning')
        return redirect(url_for('prompts.list'))
    # Get all responses for these prompts
    responses = []
    for prompt_id in prompt_ids:
        prompt_responses = response_service.get_responses_for_prompt(int(prompt_id))
        responses.extend(prompt_responses)
    if not responses:
        flash('No responses found for the selected prompts', 'info')
        return redirect(url_for('prompts.list'))
    # Clear any existing response filters first
    if 'response_ids' in session:
        session.pop('response_ids')
    # Store response IDs as strings in session
    session['response_ids'] = [str(r.response_id) for r in responses]
    # Use a redirect approach with appropriate source info
    return redirect(url_for('responses.list', 
                           source='prompt_batch', 
                           prompt_count=len(prompt_ids)))

@responses_bp.route('/view_story_responses')
def view_story_responses():
    """View all responses related to stories selected in session"""
    # Get story IDs from session
    story_ids = session.get('story_ids', [])
    
    if not story_ids:
        flash('No stories selected. Please select at least one story.', 'warning')
        return redirect(url_for('stories.list'))
    
    # Get all responses for these stories
    responses = response_service.get_responses_for_stories(story_ids)
    
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
    return redirect(url_for('responses.list', 
                           source='story', 
                           story_count=story_count,
                           story_id=story_ids[0] if story_count == 1 else None))

@responses_bp.route('/view_template_responses')
def view_template_responses():
    """View all responses related to templates selected in session"""
    # Get template IDs from session
    template_ids = session.get('template_ids', [])
    
    if not template_ids:
        flash('No templates selected. Please select at least one template.', 'warning')
        return redirect(url_for('templates.list'))
    
    # Get all responses for these templates
    responses = response_service.get_responses_for_templates(template_ids)
    
    if not responses:
        flash('No responses found for the selected templates', 'info')
        return redirect(url_for('templates.list'))
    
    # Clear any existing response filters first
    if 'response_ids' in session:
        session.pop('response_ids')
    
    # Store response IDs as strings in session
    session['response_ids'] = [str(r.response_id) for r in responses]
    
    # Generate appropriate message based on count
    template_count = len(template_ids)
    
    # Use a redirect approach
    return redirect(url_for('responses.list', 
                           source='template', 
                           template_count=template_count,
                           template_id=template_ids[0] if template_count == 1 else None))

@responses_bp.route('/responses_for_run', methods=['GET', 'POST'])
def responses_for_run():
    """
    Display and allow review/flagging of all LLM responses for the current run (job).
    - On GET: Shows all responses for the run (from session or async_service).
    - On POST: Updates flag/review notes for a single response, then reloads the page.
    """
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        if response_id:
            flagged_for_review = f'flagged_for_review_{response_id}' in request.form
            review_notes = request.form.get(f'review_notes_{response_id}', '')
            success, message = response_service.update_response_flag_and_notes(
                response_id, flagged_for_review, review_notes
            )
            flash(message, 'success' if success else 'danger')
        return redirect(url_for('responses.responses_for_run'))

    response_ids = response_service.get_response_ids_for_run(session, async_service)
    response_list, is_batch_rerun = response_service.build_response_list(response_ids)

    model = session.get('model') if not is_batch_rerun else None
    provider = session.get('provider') if not is_batch_rerun else None
    question_id = session.get('question_id')
    question = db.session.query(Question).get(question_id).content if question_id and not is_batch_rerun else None

    return render_template(
        'llm_response.html',
        response_list=response_list,
        is_batch_rerun=is_batch_rerun,
        model=model,
        provider=provider,
        question=question
    )