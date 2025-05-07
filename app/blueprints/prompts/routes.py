import datetime
from flask import flash, render_template, request, redirect, url_for, session, jsonify
from ...services import prompt_service
from . import prompts_bp

@prompts_bp.route('/list', methods=['GET', 'POST'])
def list():
    if request.method == 'POST':
        # Process form data for prompt updates if needed
        # (Similar to view_responses POST handler but for prompts)
        return redirect(url_for('prompts.list', **request.args))
        
    # Initialize prompt_ids for selection
    selected_prompt_ids = session.get('prompt_ids', [])
    
    # GET request - handle filtering
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    question_id = request.args.get('question_id', '')
    story_id = request.args.get('story_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort = request.args.get('sort', 'date_desc')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Validate date formats
    if start_date:
        try:
            datetime.datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            flash(f"Invalid start date format: {start_date}", "warning")
            start_date = ''
    
    if end_date:
        try:
            datetime.datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            flash(f"Invalid end date format: {end_date}", "warning")
            end_date = ''
    
    # Get filtered prompts using the service
    pagination = prompt_service.get_filtered_prompts(
        page=page,
        per_page=per_page,
        provider=provider,
        model=model,
        question_id=question_id,
        story_id=story_id,
        start_date=start_date,
        end_date=end_date,
        sort=sort
    )
    
    # Get filter options
    filter_options = prompt_service.get_filter_options()
    
    return render_template('see_all_prompts.html', 
                          prompts=pagination.items,
                          pagination=pagination,
                          providers=filter_options['providers'],
                          models=filter_options['models'],
                          questions=filter_options['questions'],
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

@prompts_bp.route('/update_selection', methods=['POST'])
def update_selection():
    """AJAX endpoint to update prompt selection in session"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    data = request.get_json()
    current_selection = session.get('prompt_ids', [])
    
    # Determine the action type
    if data.get('action') == 'clear_all':
        action = 'clear_all'
    elif data.get('action') == 'select_multiple':
        action = 'select_multiple'
    elif data.get('action') == 'invert_selection':
        action = 'invert_selection'
    else:
        action = 'toggle'
        
    # Update the selection using the service
    updated_selection = prompt_service.update_prompt_selection(
        current_selection=current_selection,
        action=action,
        data=data
    )
    
    # Store updated selection in session
    session['prompt_ids'] = updated_selection
    
    return jsonify({
        'success': True,
        'selected_count': len(updated_selection),
        'selected_ids': updated_selection
    })