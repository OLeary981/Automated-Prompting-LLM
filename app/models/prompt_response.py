from app import db


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
    flagged_for_review = db.Column(db.Boolean, default=False)
    review_notes = db.Column(db.Text)

    prompt = db.relationship('Prompt', backref=db.backref('responses', lazy=True))
    run_id = db.Column(db.Integer, db.ForeignKey('run.run_id', ondelete ='RESTRICT'), nullable=False) #added as part of run migration

    def __repr__(self):
        return f'<Response {self.response_id}>'
