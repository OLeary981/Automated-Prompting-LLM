from app import db

class Category(db.Model):
    __tablename__ = 'category'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Category {self.category_id} - {self.category}>'