import datetime
from sqlalchemy import func, select
from ..models import Prompt, Model, Provider, Story, Question, Response
from .. import db
from ..utils.pagination import Pagination


def get_filtered_prompts(
    page=1, 
    per_page=20, 
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
    stmt = (
        select(Prompt, func.max(Response.timestamp).label('last_used'))
        .join(Model, Prompt.model_id == Model.model_id)
        .join(Provider, Model.provider_id == Provider.provider_id)
        .join(Story, Prompt.story_id == Story.story_id)
        .join(Question, Prompt.question_id == Question.question_id)
        .outerjoin(Response, Prompt.prompt_id == Response.prompt_id)
        .group_by(Prompt.prompt_id)
    )

    # Filters
    if provider:
        stmt = stmt.where(Provider.provider_name.ilike(f"%{provider}%"))
    if model:
        stmt = stmt.where(Model.name.ilike(f"%{model}%"))
    if question_id:
        stmt = stmt.where(Prompt.question_id == question_id)
    if story_id:
        stmt = stmt.where(Prompt.story_id == story_id)

    if start_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            stmt = stmt.where(Response.timestamp >= start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            stmt = stmt.where(Response.timestamp < end_date_obj)
        except ValueError:
            pass

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
    providers = db.session.query(Provider).all()
    models = db.session.query(Model).all()
    questions = db.session.query(Question).all()
    
    return {
        'providers': providers,
        'models': models,
        'questions': questions
    }

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
        
    return db.session.query(Prompt).filter(Prompt.prompt_id.in_(prompt_ids)).all()

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
    selected_prompt_ids = current_selection.copy() if current_selection else []
    
    if action == 'clear_all':
        selected_prompt_ids = []
    
    elif action == 'select_multiple':
        prompt_ids = data.get('prompt_ids', [])
        for prompt_id in prompt_ids:
            prompt_id = str(prompt_id)
            if prompt_id not in selected_prompt_ids:
                selected_prompt_ids.append(prompt_id)
    
    elif action == 'invert_selection':
        select_ids = [str(pid) for pid in data.get('select_ids', [])]
        deselect_ids = [str(pid) for pid in data.get('deselect_ids', [])]
        
        # Add new selections
        for pid in select_ids:
            if pid not in selected_prompt_ids:
                selected_prompt_ids.append(pid)
                
        # Remove deselections
        selected_prompt_ids = [pid for pid in selected_prompt_ids if pid not in deselect_ids]
    
    elif action == 'toggle':
        prompt_id = str(data.get('prompt_id'))
        is_selected = data.get('selected', False)
        
        if is_selected and prompt_id not in selected_prompt_ids:
            selected_prompt_ids.append(prompt_id)
        elif not is_selected and prompt_id in selected_prompt_ids:
            selected_prompt_ids.remove(prompt_id)
    
    return selected_prompt_ids