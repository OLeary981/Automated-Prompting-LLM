from app import db



class Story(db.Model):
    __tablename__ = 'story'

    story_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('template.template_id'), nullable=True)

    template = db.relationship('Template', backref=db.backref('stories', lazy=True))

    def __repr__(self):
        return f'<Story {self.story_id} - {self.content}>'   
class Category(db.Model):
    __tablename__ = 'category'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Category {self.category_id} - {self.category}>'

# StoryCategory Table (Many-to-Many Relationship)
class StoryCategory(db.Model):
    __tablename__ = 'story_category'

    story_id = db.Column(db.Integer, db.ForeignKey('story.story_id', ondelete = 'CASCADE'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id', ondelete = 'CASCADE'), primary_key=True)

    story = db.relationship('Story', backref=db.backref('story_categories', lazy=True))
    category = db.relationship('Category', backref=db.backref('story_categories', lazy=True))

    def __repr__(self):
        return f'<StoryCategory {self.story_id} - {self.category_id}>'

