import json

def register_json_filters(app):
    @app.template_filter('from_json')
    def from_json(value):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    
    @app.template_filter('tojson')
    def to_json(value):
        return json.dumps(value)