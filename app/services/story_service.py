from app import db
from app.models import Story, StoryCategory

def add_story(content, category_ids=None):
    """Add a new story to the database with optional categories"""
    story = Story(content=content)
    db.session.add(story)
    db.session.flush()  # Get the story_id before committing
    
    # Add categories if provided
    if category_ids:
        for category_id in category_ids:
            story_category = StoryCategory(story_id=story.story_id, category_id=category_id)
            db.session.add(story_category)
    
    db.session.commit()
    return story.story_id

def get_all_stories():
    return Story.query.all()

def get_story_by_id(story_id):
    return Story.query.get_or_404(story_id)