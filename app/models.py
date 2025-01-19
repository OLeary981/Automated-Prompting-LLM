from app import db

# Question Table
class Question(db.Model):
    __tablename__ = 'question'

    question_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Question {self.id} - {self.content}>'

# Template Table
class Template(db.Model):
    __tablename__ = 'template'

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.id} - {self.content}>'

# Story Table
class Story(db.Model):
    __tablename__ = 'story'

    story_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('template.template_id'), nullable=False)

    template = db.relationship('Template', backref=db.backref('stories', lazy=True))

    def __repr__(self):
        return f'<Story {self.id} - {self.content}>'

# Category Table
class Category(db.Model):
    __tablename__ = 'category'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Category {self.category_id} - {self.category}>'

# StoryCategory Table (Many-to-Many Relationship)
class StoryCategory(db.Model):
    __tablename__ = 'story_category'

    story_id = db.Column(db.Integer, db.ForeignKey('story.story_id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), primary_key=True)

    story = db.relationship('Story', backref=db.backref('story_categories', lazy=True))
    category = db.relationship('Category', backref=db.backref('story_categories', lazy=True))

    def __repr__(self):
        return f'<StoryCategory {self.story_id} - {self.category_id}>'

# Provider Table
class Provider(db.Model):
    __tablename__ = 'provider'

    provider_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider_name = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Provider {self.provider_id} - {self.provider_name}>'

# Model Table
class Model(db.Model):
    __tablename__ = 'model'

    model_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_name = db.Column(db.String(255), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.provider_id'), nullable=False)

    provider = db.relationship('Provider', backref=db.backref('models', lazy=True))

    def __repr__(self):
        return f'<Model {self.model_id} - {self.model_name}>'

# Prompt Table
class Prompt(db.Model):
    __tablename__ = 'prompt'

    prompt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_id = db.Column(db.Integer, db.ForeignKey('model.model_id'), nullable=False)
    temperature = db.Column(db.Float, nullable=True)
    max_tokens = db.Column(db.Integer, nullable=True)
    top_p = db.Column(db.Float, nullable=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.story_id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.question_id'), nullable=False)
    payload = db.Column(db.Text, nullable=False)

    model = db.relationship('Model', backref=db.backref('prompts', lazy=True))
    story = db.relationship('Story', backref=db.backref('prompts', lazy=True))
    question = db.relationship('Question', backref=db.backref('prompts', lazy=True))

    def __repr__(self):
        return f'<Prompt {self.prompt_id}>'

# Response Table
class Response(db.Model):
    __tablename__ = 'response'

    response_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt.prompt_id'), nullable=False)
    response_content = db.Column(db.Text, nullable=False)
    full_response = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    prompt = db.relationship('Prompt', backref=db.backref('responses', lazy=True))

    def __repr__(self):
        return f'<Response {self.response_id}>'

# Word Table
class Word(db.Model):
    __tablename__ = 'word'

    word_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word = db.Column(db.String(255), unique=True, nullable=False)
    fields = db.relationship('Field', secondary='word_field', backref=db.backref('words', lazy='dynamic'))

    def __repr__(self):
        return f'<Word {self.word_id} - {self.word}>'

# Field Table
class Field(db.Model):
    __tablename__ = 'field'

    field_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field = db.Column(db.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f'<Field {self.field_id} - {self.field}>'

# WordField Table (Many-to-Many Relationship)
class WordField(db.Model):
    __tablename__ = 'word_field'

    word_id = db.Column(db.Integer, db.ForeignKey('word.word_id'), primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('field.field_id'), primary_key=True)

    word = db.relationship('Word', backref=db.backref('word_fields', lazy=True, overlaps="fields,words"))
    field = db.relationship('Field', backref=db.backref('word_fields', lazy=True, overlaps="fields,words"))

    def __repr__(self):
        return f'<WordField {self.word_id} - {self.field_id}>'
