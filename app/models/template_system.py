from app import db


# Template Table
class Template(db.Model):
    __tablename__ = 'template'

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.id} - {self.content}>'

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

# Field Table
class Field(db.Model):
    __tablename__ = 'field'

    field_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field = db.Column(db.String(255), unique=True, nullable=False)

    # Many-to-Many Relationship
    words = db.relationship('Word', secondary=word_field_association, back_populates='fields')

    def __repr__(self):
        return f'<Field {self.field_id} - {self.field}>'