import datetime
from flask import flash, render_template, request, redirect, url_for, session, jsonify
from ...services import prompt_service
from . import prompts_bp

@prompts_bp.route('/list', methods=['GET', 'POST'])
def list():
    if request.method == 'POST':
        return redirect(url_for('prompts.list', **request.args))

    selected_prompt_ids = session.get('prompt_ids', [])

    # Collect filter params
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
    for date_param, label in [(start_date, "start date"), (end_date, "end date")]:
        try:
            if date_param:
                datetime.datetime.strptime(date_param, "%Y-%m-%d")
        except ValueError:
            flash(f"Invalid {label} format: {date_param}", "warning")

    # Use the updated service
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

    filter_options = prompt_service.get_filter_options()

    return render_template(
        'see_all_prompts.html',
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
        }
    )

@prompts_bp.route('/update_selection', methods=['POST'])
def update_selection():
    """AJAX endpoint to update prompt selection in session"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    data = request.get_json()
    current_selection = session.get('prompt_ids', [])

    # Handle single-prompt selection for the "View All Responses for this Prompt" button
    if data.get('action') == 'select_single' and data.get('prompt_id'):
        session['prompt_ids'] = [str(data['prompt_id'])]
        return jsonify({
            'success': True,
            'selected_count': 1,
            'selected_ids': [str(data['prompt_id'])]
        })

    # Existing logic for other actions
    if data.get('action') == 'clear_all':
        action = 'clear_all'
    elif data.get('action') == 'select_multiple':
        action = 'select_multiple'
    elif data.get('action') == 'invert_selection':
        action = 'invert_selection'
    else:
        action = 'toggle'

    updated_selection = prompt_service.update_prompt_selection(
        current_selection=current_selection,
        action=action,
        data=data
    )

    session['prompt_ids'] = updated_selection

    return jsonify({
        'success': True,
        'selected_count': len(updated_selection),
        'selected_ids': updated_selection
    })