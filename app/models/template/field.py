from app import db
from .word import word_field_association
# Field Table
class Field(db.Model):
    __tablename__ = 'field'

    field_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field = db.Column(db.String(255), unique=True, nullable=False)

    # Many-to-Many Relationship
    words = db.relationship('Word', secondary=word_field_association, back_populates='fields')

    def __repr__(self):
        return f'<Field {self.field_id} - {self.field}>'