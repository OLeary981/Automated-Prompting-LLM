from app import db

# Association Table (No Explicit Model Needed)
word_field_association = db.Table(
    'word_field',
    db.Column('word_id', db.Integer, db.ForeignKey('word.word_id'), primary_key=True),
    db.Column('field_id', db.Integer, db.ForeignKey('field.field_id'), primary_key=True)
)

# Word Table
class Word(db.Model):
    __tablename__ = 'word'

    word_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word = db.Column(db.String(255), unique=True, nullable=False)

    # Many-to-Many Relationship
    fields = db.relationship('Field', secondary=word_field_association, back_populates='words')

    def __repr__(self):
        return f'<Word {self.word_id} - {self.word}>'