from app import db


# Story Table
class Story(db.Model):
    __tablename__ = 'story'

    story_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('template.template_id'), nullable=False)

    template = db.relationship('Template', backref=db.backref('stories', lazy=True))

    def __repr__(self):
        return f'<Story {self.id} - {self.content}>'

# StoryCategory Table (Many-to-Many Relationship)
class StoryCategory(db.Model):
    __tablename__ = 'story_category'

    story_id = db.Column(db.Integer, db.ForeignKey('story.story_id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), primary_key=True)

    story = db.relationship('Story', backref=db.backref('story_categories', lazy=True))
    category = db.relationship('Category', backref=db.backref('story_categories', lazy=True))

    def __repr__(self):
        return f'<StoryCategory {self.story_id} - {self.category_id}>'
