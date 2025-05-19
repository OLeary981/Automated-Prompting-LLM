import csv
import datetime
import io

from flask import (
    Response as FlaskResponse,
)
from flask import (
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

from ... import db
from ...models import Model, Prompt, Provider, Question, Response, Story, Template
from ...services import async_service, response_service
from . import responses_bp

# def clear_selected_filters(request, session, keys):
#     print("Clearing selected filters")
#     for key in keys:
#         if f'clear_{key}' in request.args and f'{key}_ids' in session:
#             print(f"Clearing {key}_ids from session")
#             session.pop(f'{key}_ids')

# def clear_selected_filters(request, session, keys):
#     print("Clearing selected filters")
#     # Map singular forms to correct plural forms for request args
#     mappings = {
#         'story': 'stories',
#         'prompt': 'prompts', 
#         'response': 'responses',
#         'template': 'templates'
#     }
    
#     for key in keys:
#         # Use the mapping to get the correct plural form
#         plural_form = mappings.get(key, key + 's')
#         request_key = f'clear_{plural_form}'
#         session_key = f'{key}_ids'
        
#         print(f"Checking for {request_key} in args")
#         if request_key in request.args and session_key in session:
#             print(f"Clearing {session_key} from session")
#             session.pop(session_key)


@responses_bp.route('/list', methods=['GET', 'POST'])
def list():
    if request.method == 'POST':
        response_id = request.form.get('response_id')
        if response_id:
            flagged_key = f'flagged_for_review_{response_id}'
            flagged_for_review = flagged_key in request.form
            notes_key = f'review_notes_{response_id}'
            review_notes = request.form.get(notes_key, '')

            success, error = response_service.update_response_review(
                response_id, flagged_for_review, review_notes
            )

            if success:
                flash(f'Response {response_id} updated successfully!', 'success')
            else:
                flash(f'Error updating response: {error}', 'danger')

        return redirect(url_for('responses.list', **request.args))

    # clear_selected_filters(request, session, ['story', 'response', 'template', 'prompt'])
    print("URL Args:", dict(request.args))
    print("Session before:", {k: v for k, v in session.items() if '_ids' in k})
    
    # Clear flags processing
    if 'clear_stories' in request.args and 'story_ids' in session:
        session.pop('story_ids')
        print("Cleared story_ids")
        
    if 'clear_responses' in request.args and 'response_ids' in session:
        session.pop('response_ids')
        print("Cleared response_ids")
    
    if 'clear_templates' in request.args and 'template_ids' in session:
        session.pop('template_ids')
        print("Cleared template_ids")
        
    if 'clear_prompts' in request.args and 'prompt_ids' in session:
        session.pop('prompt_ids')
        print("Cleared prompt_ids")
    
    print("Session after:", {k: v for k, v in session.items() if '_ids' in k})

    run_id = request.args.get('run_id', '')
    filter_kwargs = response_service.build_filter_kwargs(request, session)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config["PER_PAGE"], type=int)
    source = request.args.get('source', '')
    source_id = request.args.get('source_id') or request.args.get('prompt_id') or request.args.get('story_id') or request.args.get('template_id')
    source_count = request.args.get('story_count') or request.args.get('template_count')

    pagination = response_service.get_responses_paginated(
        page=page,
        per_page=per_page,
        **filter_kwargs
    )

    if not pagination.items:
        flash('No responses found for this selection', 'info')

    filter_options = response_service.get_dynamic_filter_options(
        run_id=run_id,
        story_ids=session.get('story_ids'),
        template_ids=session.get('template_ids'),
        prompt_ids=session.get('prompt_ids')
    )

    response_ids = session.get('response_ids', [])
    provider = request.args.get('provider', '')
    model = request.args.get('model', '')
    question_id = request.args.get('question_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    flagged_only = bool(request.args.get('flagged_only'))
    sort = request.args.get('sort', 'date_desc')

    has_response_filter = bool(response_ids and 'clear_responses' not in request.args)
    has_secondary_filters = any([provider, model, flagged_only, question_id, start_date, end_date])

    runs = response_service.get_valid_runs(
        story_ids=session.get('story_ids'),
        template_ids=session.get('template_ids'),
        prompt_ids=session.get('prompt_ids')
    )

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
        source_info=response_service.get_source_info(source, source_id, source_count),
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
        runs=runs
    )


@responses_bp.route('/export', methods=['GET'])
def export():
    filter_kwargs = response_service.build_filter_kwargs(request, session)
    stmt = response_service.build_response_query(**filter_kwargs)
    responses = db.session.execute(stmt).scalars().all()

    csv_data = response_service.generate_csv_export(responses)

    return send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'responses_export_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
    )


@responses_bp.route('/update_response_flag', methods=['POST'])
def update_response_flag():
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    data = request.get_json()
    response_id = data.get('response_id')
    flagged = data.get('flagged', False)

    success, error = response_service.update_response_flag(response_id, flagged)

    if success:
        return jsonify({'success': True, 'response_id': response_id, 'flagged': flagged})
    else:
        return jsonify({'success': False, 'message': error}), 500


@responses_bp.route('/view_prompt_responses')
def view_prompt_responses():
    prompt_ids = session.get('prompt_ids', [])
    if isinstance(prompt_ids, (str, int)):
        prompt_ids = [prompt_ids]
    if not prompt_ids:
        flash('No prompts selected. Please select at least one prompt.', 'warning')
        return redirect(url_for('prompts.list'))

    session.pop('response_ids', None)
    session['prompt_ids'] = [str(pid) for pid in prompt_ids]

    return redirect(url_for('responses.list', source='prompt_batch', prompt_count=len(prompt_ids)))


@responses_bp.route('/view_story_responses')
def view_story_responses():
    story_ids = session.get('story_ids', [])
    if not story_ids:
        flash('No stories selected. Please select at least one story.', 'warning')
        return redirect(url_for('stories.list'))

    responses = response_service.get_responses_for_stories(story_ids)
    if not responses:
        flash('No responses found for the selected stories', 'info')
        return redirect(url_for('stories.list'))

    session.pop('response_ids', None)
    session['response_ids'] = [str(r.response_id) for r in responses]
    story_count = len(story_ids)

    return redirect(url_for('responses.list', source='story', story_count=story_count, story_id=story_ids[0] if story_count == 1 else None))


@responses_bp.route('/view_template_responses')
def view_template_responses():
    template_ids = session.get('template_ids', [])
    if not template_ids:
        flash('No templates selected. Please select at least one template.', 'warning')
        return redirect(url_for('templates.list'))

    responses = response_service.get_responses_for_templates(template_ids)
    if not responses:
        flash('No responses found for the selected templates', 'info')
        return redirect(url_for('templates.list'))

    session.pop('response_ids', None)
    session['response_ids'] = [str(r.response_id) for r in responses]
    template_count = len(template_ids)

    return redirect(url_for('responses.list', source='template', template_count=template_count, template_id=template_ids[0] if template_count == 1 else None))


@responses_bp.route('/responses_for_run', methods=['GET', 'POST'])
def responses_for_run():
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
