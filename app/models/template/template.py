from app import db


# Template Table
class Template(db.Model):
    __tablename__ = 'template'

    template_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.template_id} - {self.content}>'



