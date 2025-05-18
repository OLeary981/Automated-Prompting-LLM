from .. import db


class Run(db.Model):
    __tablename__ = 'run'
    run_id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    description = db.Column(db.String(255))
    # Can add more field later? 

    
    # Relationship to responses - each run can have multiple responses
    responses = db.relationship('Response', backref='run', lazy=True)