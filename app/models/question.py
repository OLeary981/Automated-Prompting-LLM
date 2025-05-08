from app import db
# Question Table
class Question(db.Model):
    __tablename__ = 'question'

    question_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Question {self.question_id} - {self.content}>'