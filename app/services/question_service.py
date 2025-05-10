from app import db
from app.models import Question

def get_all_questions():
    return Question.query.all()


def add_question(content):
    new_question = Question(content=content)
    db.session.add(new_question)
    db.session.commit()
    return new_question.question_id

def get_question_by_id(question_id):
    return db.session.get(Question, question_id)