import csv
import datetime
import io
from sqlalchemy import func

from ..models import Response, Prompt, Model, Provider, Story, Question, Template
from .. import db

def build_response_query(
    provider=None, 
    model=None, 
    flagged_only=False, 
    question_id=None, 
    story_id=None, 
    template_ids=None,
    response_ids=None,
    story_ids=None,
    start_date=None, 
    end_date=None, 
    sort='date_desc'
):
    """
    Build a query for responses with all filters applied
    """
    # Base query with all necessary joins
    query = db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Model, Prompt.model_id == Model.model_id).\
        join(Provider, Model.provider_id == Provider.provider_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        join(Question, Prompt.question_id == Question.question_id)
    
    # Apply filters based on specific response IDs (highest priority)
    if response_ids:
        # Convert string IDs to integers if necessary
        if isinstance(response_ids[0], str):
            int_response_ids = [int(rid) for rid in response_ids]
        else:
            int_response_ids = response_ids
        query = query.filter(Response.response_id.in_(int_response_ids))
        
    # Filter by story IDs
    elif story_ids:
        # Convert string IDs to integers if necessary
        if isinstance(story_ids[0], str):
            int_story_ids = [int(sid) for sid in story_ids]
        else:
            int_story_ids = story_ids
        query = query.filter(Prompt.story_id.in_(int_story_ids))
        
    # Filter by template IDs - stories that use these templates
    elif template_ids:
        # Convert string IDs to integers if necessary
        if isinstance(template_ids[0], str):
            int_template_ids = [int(tid) for tid in template_ids]
        else:
            int_template_ids = template_ids
        # First, get stories that use these templates
        story_subquery = db.session.query(Story.story_id).filter(Story.template_id.in_(int_template_ids))
        # Then filter prompts by those stories
        query = query.filter(Prompt.story_id.in_(story_subquery))
    
    # Apply standard filters
    if provider:
        query = query.filter(Provider.provider_name.ilike(f'%{provider}%'))
    if model:
        query = query.filter(Model.name.ilike(f'%{model}%'))
    if flagged_only:
        query = query.filter(Response.flagged_for_review.is_(True))
    if question_id:
        query = query.filter(Prompt.question_id == question_id)
    if story_id:
        query = query.filter(Prompt.story_id == story_id)
    
    # Apply date range filters
    if start_date:
        try:
            if isinstance(start_date, str):
                start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_date_obj = start_date
            query = query.filter(Response.timestamp >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            if isinstance(end_date, str):
                # Add one day to include the end date fully
                end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            else:
                end_date_obj = end_date + datetime.timedelta(days=1)
            query = query.filter(Response.timestamp < end_date_obj)
        except ValueError:
            pass
    
    # Apply sorting
    if sort == 'date_asc':
        query = query.order_by(Response.timestamp.asc())
    else:  # Default to date_desc
        query = query.order_by(Response.timestamp.desc())
    
    return query

def get_responses_paginated(
    page=1, 
    per_page=20, 
    **filter_params
):
    """
    Get paginated responses with all filters applied
    """
    query = build_response_query(**filter_params)
    return query.paginate(page=page, per_page=per_page, error_out=False)

def get_filter_options():
    """
    Get all available filter options for the responses list
    """
    providers = db.session.query(Provider).all()
    models = db.session.query(Model).all()
    questions = db.session.query(Question).all()
    
    return {
        'providers': providers,
        'models': models,
        'questions': questions
    }

def get_source_info(source, source_id=None, source_count=None):
    """
    Get display information about the source of responses
    """
    if not source:
        return None
    
    if source == 'prompt' and source_id:
        prompt = db.session.query(Prompt).get(int(source_id))
        if prompt:
            return f"Prompt #{source_id} ({prompt.model.name})"
    
    elif source == 'story':
        if source_count and int(source_count) > 1:
            return f"{source_count} Selected Stories"
        elif source_id:
            story = db.session.query(Story).get(int(source_id))
            if story:
                content_preview = story.content[:50] + '...' if len(story.content) > 50 else story.content
                return f"Story #{source_id} ({content_preview})"
    
    elif source == 'template':
        if source_count and int(source_count) > 1:
            return f"{source_count} Selected Templates"
        elif source_id:
            template = db.session.query(Template).get(int(source_id))
            if template:
                content_preview = template.content[:50] + '...' if len(template.content) > 50 else template.content
                return f"Template #{source_id} ({content_preview})"
    
    return None

def update_response_flag(response_id, flagged):
    """
    Update a response's flag status
    """
    response = db.session.query(Response).get(response_id)
    if not response:
        return False, "Response not found"
    
    try:
        response.flagged_for_review = flagged
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def update_response_review(response_id, flagged_for_review, review_notes):
    """
    Update a response's flag status and review notes
    """
    response = db.session.query(Response).get(response_id)
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
    return db.session.query(Response).filter(Response.prompt_id == prompt_id).all()

def get_responses_for_stories(story_ids):
    """
    Get all responses for a list of stories
    """
    if isinstance(story_ids[0], str):
        int_story_ids = [int(sid) for sid in story_ids]
    else:
        int_story_ids = story_ids
        
    return db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        filter(Prompt.story_id.in_(int_story_ids)).all()

def get_responses_for_templates(template_ids):
    """
    Get all responses for a list of templates
    """
    if isinstance(template_ids[0], str):
        int_template_ids = [int(tid) for tid in template_ids]
    else:
        int_template_ids = template_ids
        
    return db.session.query(Response).\
        join(Prompt, Response.prompt_id == Prompt.prompt_id).\
        join(Story, Prompt.story_id == Story.story_id).\
        filter(Story.template_id.in_(int_template_ids)).all()

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