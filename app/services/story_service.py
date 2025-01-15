from app import db
from app.models import Story

def add_story(content):
    new_story = Story(content=content)
    db.session.add(new_story)
    db.session.commit()
    return new_story.story_id

def get_all_stories():
    return Story.query.all()

def get_story_by_id(story_id):
    return Story.query.get_or_404(story_id)