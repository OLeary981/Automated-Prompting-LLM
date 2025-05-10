from app import db
from app.models import Story, StoryCategory
from flask import abort

def add_story(content, category_ids=None, template_id=None):
    story = Story(content=content, template_id=template_id)
    db.session.add(story)
    db.session.flush()
    if category_ids:
        for category_id in category_ids:
            db.session.add(StoryCategory(story_id=story.story_id, category_id=category_id))
    db.session.commit()
    return story.story_id

def add_story_with_categories(content, category_ids, new_category=None):
    from app.services import category_service  # Avoid circular import
    if new_category and new_category.strip():
        new_category_id = category_service.add_category(new_category.strip())
        if new_category_id not in category_ids:
            category_ids.append(new_category_id)
    return add_story(content, category_ids)

def get_all_stories():
    return Story.query.all()

def get_story_by_id(story_id):
    story = db.session.get(Story, story_id)
    if story is None:
        abort(404) #chose this instead of a flash message or a custom error with an API in mind for the future.
    return story

def delete_story(story_id):
    """Delete a story by ID"""
    story = db.session.query(Story).filter(Story.story_id == story_id).first()
    if story:
        db.session.delete(story)
        db.session.commit()
        return True
    return False