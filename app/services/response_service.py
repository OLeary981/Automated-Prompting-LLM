import csv
import datetime
import io
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import func, select

from app.utils.pagination import Pagination

from .. import db
from ..models import Model, Prompt, Provider, Question, Response, Run, Story, Template


def _to_int_list(id_list: List[Union[str, int]]) -> List[int]:
    """Convert a list of IDs to integers."""
    return [int(x) for x in id_list]

def get_all_runs():
    stmt = select(Run).order_by(Run.run_id.desc())
    return db.session.execute(stmt).scalars().all()

def update_response_flag_and_notes(response_id, flagged_for_review, review_notes):
    """Update the flagged_for_review and review_notes fields for a single response."""
    
    try:
        response = db.session.query(Response).get(response_id)
        if response:
            response.flagged_for_review = flagged_for_review
            response.review_notes = review_notes
            db.session.commit()
            return True, f'Response {response_id} updated successfully!'
        else:
            return False, f'Error: Response {response_id} not found.'
    except Exception as e:
        db.session.rollback()
        return False, f'Error updating response: {str(e)}'

def get_response_ids_for_run(session, async_service):
    """Get response IDs for the current run from async_service or session."""
    response_ids = []
    job_id = session.get('job_id')
    if job_id and job_id in async_service.processing_jobs:
        job = async_service.processing_jobs[job_id]
        for result_data in job["results"].values():
            if isinstance(result_data, dict) and "response_id" in result_data:
                response_ids.append(str(result_data["response_id"]))
        job["response_ids"] = response_ids
        if response_ids:
            session['response_ids'] = response_ids
    if not response_ids:
        response_ids = session.get('response_ids', [])
    return response_ids

def build_response_list(response_ids):
    """Build a list of response data dicts for the template and detect batch rerun."""
    
    response_list = []
    unique_models = set()
    unique_providers = set()
    unique_questions = set()
    for response_id in response_ids:
        response = db.session.query(Response).get(response_id)
        if response:
            prompt = response.prompt
            story = prompt.story
            question = prompt.question
            model = prompt.model
            unique_models.add(model.name)
            unique_providers.add(model.provider.provider_name)
            unique_questions.add(question.content)
            response_data = {
                'response_id': response.response_id,
                'response_content': response.response_content,
                'flagged_for_review': response.flagged_for_review,
                'review_notes': response.review_notes,
                'story': story,
                'question': question.content,
                'model': model.name,
                'provider': model.provider.provider_name,
                'temperature': prompt.temperature,
                'max_tokens': prompt.max_tokens,
                'top_p': prompt.top_p
            }
            response_list.append(response_data)
    is_batch_rerun = (len(unique_models) > 1 or len(unique_providers) > 1 or len(unique_questions) > 1)
    return response_list, is_batch_rerun



def build_response_query(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    flagged_only: bool = False,
    question_id: Optional[int] = None,
    story_id: Optional[int] = None,
    template_ids: Optional[List[Union[str, int]]] = None,
    response_ids: Optional[List[Union[str, int]]] = None,
    story_ids: Optional[List[Union[str, int]]] = None,
    start_date: Optional[Union[str, datetime.datetime]] = None,
    end_date: Optional[Union[str, datetime.datetime]] = None,
    sort: str = 'date_desc',
    run_id: Optional[Union[str, int]] = None,
):
    """
    Build a query for responses with all filters applied.
    """
    stmt = select(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Model, Prompt.model_id == Model.model_id).\
        join(Provider, Model.provider_id == Provider.provider_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        join(Question, Prompt.question_id == Question.question_id)

    if response_ids:
        stmt = stmt.filter(Response.response_id.in_(_to_int_list(response_ids)))
    elif story_ids:
        stmt = stmt.filter(Prompt.story_id.in_(_to_int_list(story_ids)))
    elif template_ids:
        story_subquery = select(Story.story_id).filter(Story.template_id.in_(_to_int_list(template_ids)))
        stmt = stmt.filter(Prompt.story_id.in_(story_subquery))

    if provider:
        stmt = stmt.filter(Provider.provider_name.ilike(f'%{provider}%'))
    if model:
        stmt = stmt.filter(Model.name.ilike(f'%{model}%'))
    if flagged_only:
        stmt = stmt.filter(Response.flagged_for_review.is_(True))
    if question_id:
        stmt = stmt.filter(Prompt.question_id == question_id)
    if story_id:
        stmt = stmt.filter(Prompt.story_id == story_id)
    if run_id:
        stmt = stmt.filter(Response.run_id == int(run_id))

    if start_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d') if isinstance(start_date, str) else start_date
            stmt = stmt.filter(Response.timestamp >= start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1) if isinstance(end_date, str) else end_date + datetime.timedelta(days=1)
            stmt = stmt.filter(Response.timestamp < end_date_obj)
        except ValueError:
            pass

    if sort == 'date_asc':
        stmt = stmt.order_by(Response.timestamp.asc())
    else:
        stmt = stmt.order_by(Response.timestamp.desc())

    return stmt

def get_responses_paginated(
    page: int,
    per_page: int,
    **filter_params
) -> Pagination:
    """
    Get paginated responses with all filters applied, using custom Pagination class.
    """
    stmt = build_response_query(**filter_params)
    total = db.session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar()
    items = db.session.execute(
        stmt.offset((page - 1) * per_page).limit(per_page)
    ).scalars().all()
    return Pagination(items, page, per_page, total)

def get_filter_options() -> Dict[str, Any]:
    """
    Get all available filter options for the responses list.
    """
    providers = db.session.execute(select(Provider)).scalars().all()
    models = db.session.execute(select(Model)).scalars().all()
    questions = db.session.execute(select(Question)).scalars().all()
    return {
        'providers': providers,
        'models': models,
        'questions': questions
    }

def get_source_info(source: str, source_id: Optional[int] = None, source_count: Optional[int] = None) -> Optional[str]:
    """
    Get display information about the source of responses.
    """
    if not source:
        return None

    if source == 'prompt' and source_id:
        prompt = db.session.get(Prompt, int(source_id))
        if prompt:
            return f"Prompt #{source_id} ({prompt.model.name})"

    elif source == 'story':
        if source_count and int(source_count) > 1:
            return f"{source_count} Selected Stories"
        elif source_id:
            story = db.session.get(Story, int(source_id))
            if story:
                content_preview = story.content[:50] + '...' if len(story.content) > 50 else story.content
                return f"Story #{source_id} ({content_preview})"

    elif source == 'template':
        if source_count and int(source_count) > 1:
            return f"{source_count} Selected Templates"
        elif source_id:
            template = db.session.get(Template, int(source_id))
            if template:
                content_preview = template.content[:50] + '...' if len(template.content) > 50 else template.content
                return f"Template #{source_id} ({content_preview})"

    return None

def update_response_flag(response_id: int, flagged: bool) -> Tuple[bool, Optional[str]]:
    """
    Update a response's flag status.
    """
    response = db.session.get(Response, response_id)
    if not response:
        return False, "Response not found"
    try:
        response.flagged_for_review = flagged
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def update_response_review(response_id: int, flagged_for_review: bool, review_notes: str) -> Tuple[bool, Optional[str]]:
    """
    Update a response's flag status and review notes.
    """
    response = db.session.get(Response, response_id)
    if not response:
        return False, "Response not found"
    try:
        response.flagged_for_review = flagged_for_review
        response.review_notes = review_notes
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_responses_for_prompt(prompt_id):
    """
    Get all responses for a specific prompt
    """
    stmt = select(Response).filter(Response.prompt_id == prompt_id)
    return db.session.execute(stmt).scalars().all()

def get_responses_for_stories(story_ids):
    """
    Get all responses for a list of stories
    """
    if isinstance(story_ids[0], str):
        int_story_ids = [int(sid) for sid in story_ids]
    else:
        int_story_ids = story_ids
        
    stmt = (
        select(Response)
        .join(Prompt, Response.prompt_id == Prompt.prompt_id)
        .filter(Prompt.story_id.in_(int_story_ids))
    )
    return db.session.execute(stmt).scalars().all()

def get_responses_for_templates(template_ids):
        
    if isinstance(template_ids[0], str):
        int_template_ids = [int(tid) for tid in template_ids]
    else:
        int_template_ids = template_ids
        
    stmt = (
        select(Response)
        .join(Prompt, Response.prompt_id == Prompt.prompt_id)
        .join(Story, Prompt.story_id == Story.story_id)
        .filter(Story.template_id.in_(int_template_ids))
    )
    return db.session.execute(stmt).scalars().all()

def generate_csv_export(responses):
    """
    Generate a CSV file from a list of responses
    """
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
    
    # Return the file content
    return mem_file.getvalue()

def get_filters_for_run(run_id):
    """
    Given a run_id, return provider, model, and question_id for the first response in that run.
    """
    response = db.session.query(Response).filter_by(run_id=run_id).first()
    if not response:
        return None, None, None
    prompt = db.session.query(Prompt).get(response.prompt_id)
    if not prompt:
        return None, None, None
    model = db.session.query(Model).get(prompt.model_id)
    provider = model.provider if model else None
    return (
        provider.provider_name if provider else None,
        model.name if model else None,
        prompt.question_id
    )