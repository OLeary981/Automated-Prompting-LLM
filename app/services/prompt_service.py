import datetime

from sqlalchemy import func, select

from app import session_scope

from .. import db
from ..models import Model, Prompt, Provider, Question, Response, Story
from ..utils.pagination import Pagination


def _parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None

def _apply_filters(stmt, provider, model, question_id, story_id, start_date, end_date):
    if provider:
        stmt = stmt.where(Provider.provider_name.ilike(f"%{provider}%"))
    if model:
        stmt = stmt.where(Model.name.ilike(f"%{model}%"))
    if question_id:
        stmt = stmt.where(Prompt.question_id == question_id)
    if story_id:
        stmt = stmt.where(Prompt.story_id == story_id)
    if start_date:
        start_date_obj = _parse_date(start_date)
        if start_date_obj:
            stmt = stmt.where(Response.timestamp >= start_date_obj)
    if end_date:
        end_date_obj = _parse_date(end_date)
        if end_date_obj:
            stmt = stmt.where(Response.timestamp < end_date_obj + datetime.timedelta(days=1))
    return stmt


def get_filtered_prompts(
    page = None, 
    per_page = None, 
    provider=None, 
    model=None, 
    question_id=None, 
    story_id=None, 
    start_date=None, 
    end_date=None, 
    sort='date_desc'
):
    """
    Get filtered and paginated prompts based on criteria using SQLAlchemy 2.0 API

    Returns:
        Pagination: Custom pagination object with items and metadata
    """
    #couldn't set defaults in function declaration due to wanting to use app config as default. 
    page = page or 1
    if per_page is None:
        from flask import current_app
        per_page = current_app.config["PER_PAGE"]

    stmt = (
        select(Prompt, func.max(Response.timestamp).label('last_used'))
        .join(Model, Prompt.model_id == Model.model_id)
        .join(Provider, Model.provider_id == Provider.provider_id)
        .join(Story, Prompt.story_id == Story.story_id)
        .join(Question, Prompt.question_id == Question.question_id)
        .outerjoin(Response, Prompt.prompt_id == Response.prompt_id)
        .group_by(Prompt.prompt_id)
    )

    # Apply filters using the helper function
    stmt = _apply_filters(stmt, provider, model, question_id, story_id, start_date, end_date)

    # Sorting
    if sort == 'date_asc':
        stmt = stmt.order_by(func.max(Response.timestamp).asc())
    else:
        stmt = stmt.order_by(func.max(Response.timestamp).desc())

    # Count total (using subquery to avoid recomputing filters)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(count_stmt).scalar()

    # Pagination
    paginated_stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    items = db.session.execute(paginated_stmt).all()

    return Pagination(items=items, page=page, per_page=per_page, total=total)

def get_filter_options():
    """
    Get all available filter options for the prompt list
    
    Returns:
        dict: Dictionary containing providers, models, and questions
    """
    providers = db.session.execute(select(Provider)).scalars().all()
    models = db.session.execute(select(Model)).scalars().all()
    questions = db.session.execute(select(Question)).scalars().all()
    
    return {
        'providers': providers,
        'models': models,
        'questions': questions
    }
#feels like a basic and important function but not actually being called anywhere?! End up having to do joins to story and question for all pages anyway?
def get_prompts_by_ids(prompt_ids):
    """
    Get prompts by their IDs
    
    Args:
        prompt_ids (list): List of prompt IDs
    
    Returns:
        list: List of Prompt objects
    """
    if not prompt_ids:
        return []
    stmt = select(Prompt).where(Prompt.prompt_id.in_(prompt_ids))
    return db.session.execute(stmt).scalars().all()


def _clear_all():
    return set()

def _select_multiple(selection, prompt_ids):
    return selection.union(set(map(str, prompt_ids)))

def _invert_selection(selection, select_ids, deselect_ids):
    selection.update(map(str, select_ids))
    selection.difference_update(map(str, deselect_ids))
    return selection

def _toggle(selection, prompt_id, is_selected):
    if is_selected:
        selection.add(prompt_id)
    else:
        selection.discard(prompt_id)
    return selection



def update_prompt_selection(current_selection, action, data):
    """
    Update a list of selected prompt IDs based on action
    
    Args:
        current_selection (list): Current list of selected prompt IDs
        action (str): Action to perform ('clear_all', 'select_multiple', or 'toggle')
        data (dict): Additional data needed for the action
    
    Returns:
        list: Updated list of selected prompt IDs
    """
    selection = set(current_selection or [])
    
    if action == 'clear_all':
        selection = _clear_all()
    elif action == 'select_multiple':
        selection = _select_multiple(selection, data.get('prompt_ids', []))
    elif action == 'invert_selection':
        selection = _invert_selection(selection, data.get('select_ids', []), data.get('deselect_ids', []))
    elif action == 'toggle':
        prompt_id = str(data.get('prompt_id'))
        is_selected = data.get('selected', False)
        selection = _toggle(selection, prompt_id, is_selected)

    return list(selection)



def hydrate_prompt(prompt_id, fetch_content=True):
    """
    Hydrate a prompt with all needed data.
    
    Args:
        prompt_id: ID of the prompt to hydrate
        fetch_content: If True, fetch actual content not just IDs
        
    Returns:
        dict: Complete prompt data with related entities
    """
    with session_scope() as session:
        prompt = session.query(Prompt).get(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt ID {prompt_id} not found")
            
        result = {
            "prompt_id": prompt.prompt_id,
            "model_id": prompt.model_id,
            "story_id": prompt.story_id,
            "question_id": prompt.question_id,
            "parameters": {
                "temperature": prompt.temperature,
                "max_tokens": prompt.max_tokens,
                "top_p": prompt.top_p
            }
        }
        
        if fetch_content:
            # Optimize with join to minimize queries
            story = session.query(Story).get(prompt.story_id)
            question = session.query(Question).get(prompt.question_id)
            result["story_content"] = story.content if story else None
            result["question_content"] = question.content if question else None
            
        return result