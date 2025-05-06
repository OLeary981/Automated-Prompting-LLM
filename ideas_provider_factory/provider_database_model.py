# Add to your Provider model in models.py
class Provider(db.Model):
    provider_id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(64), nullable=False, unique=True)
    # New fields for provider factory
    module_name = db.Column(db.String(128), nullable=False)  # e.g., "groq_provider"
    config_json = db.Column(db.Text)  # JSON configuration including API keys
    display_name = db.Column(db.String(128))
    description = db.Column(db.Text)
    enabled = db.Column(db.Boolean, default=True)
    models = db.relationship('Model', backref='provider', lazy=True)