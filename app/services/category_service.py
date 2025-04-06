from .. import db
from ..models import Category, StoryCategory

def get_all_categories():
    """Get all categories from the database"""
    return db.session.query(Category).order_by(Category.category).all()

def add_category(category_name):
    """Add a new category to the database if it doesn't exist"""
    # Check if category already exists
    existing = db.session.query(Category).filter(Category.category == category_name).first()
    if existing:
        return existing.category_id
    
    # Add new category
    new_category = Category(category=category_name)
    db.session.add(new_category)
    db.session.commit()
    return new_category.category_id

def get_categories_for_story(story_id):
    """Get all categories associated with a story"""
    query = db.session.query(Category)\
        .join(StoryCategory, StoryCategory.category_id == Category.category_id)\
        .filter(StoryCategory.story_id == story_id)
    return query.all()

def set_categories_for_story(story_id, category_ids):
    """Set the categories for a story, replacing any existing associations"""
    # First, remove all existing category associations
    db.session.query(StoryCategory).filter(StoryCategory.story_id == story_id).delete()
    
    # Add new category associations
    for category_id in category_ids:
        story_category = StoryCategory(story_id=story_id, category_id=category_id)
        db.session.add(story_category)
    
    db.session.commit()