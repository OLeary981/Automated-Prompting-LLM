from app import db



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
    name = db.Column(db.String(255), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.provider_id'), nullable=False)
    endpoint = db.Column(db.String(255), nullable=True)  # Line 76: Added endpoint column
    request_delay = db.Column(db.Float, nullable=False)  # Line 77: Added request_delay column
    parameters = db.Column(db.Text, nullable=False)  # Line 78: Added parameters column

    provider = db.relationship('Provider', backref=db.backref('models', lazy=True))

    def __repr__(self):
        return f'<Model {self.model_id} - {self.name}>'

