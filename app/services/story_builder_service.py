import itertools
import re
import time
from app import db
from app.models import Template, Story, Question, Word, Field, StoryCategory
import llm as llm

def get_all_templates():
    return db.session.query(Template).all()

def get_template_fields(template_id):
    template = db.session.query(Template).get(template_id)
    field_names = re.findall(r'\{(.*?)\}', template.content)
    fields = {}
    missing_fields = []
    for field_name in field_names:
        field = db.session.query(Field).filter_by(field=field_name).first()
        if field:
            words = [word.word for word in field.words]
            fields[field_name] = words
        else:
            missing_fields.append(field_name)
    return fields, missing_fields

def add_words_to_field(field_name, new_words):
    field = db.session.query(Field).filter_by(field=field_name).first()
    if not field:
        field = Field(field=field_name)
        db.session.add(field)
        db.session.commit()
    words = [word.strip() for word in new_words.split(',')]
    for word in words:
        existing_word = db.session.query(Word).filter_by(word=word).first()
        if not existing_word:
            new_word = Word(word=word)
            field.words.append(new_word)
            db.session.add(new_word)
        else:
            if field not in existing_word.fields:
                existing_word.fields.append(field)
    db.session.commit()

def generate_permutations(fields):
    """Generate all possible permutations of field values."""
    field_names = list(fields.keys())
    return list(itertools.product(*(fields[field] for field in field_names)))

def template_filler(template, template_id, field_data=None, category_ids=None):
    """
    Fill the template with permutations of field values.
    Optionally assign categories to the generated stories.
    """
    fields, missing_fields = get_template_fields(template_id)
    
    # If field_data is provided from the form, use it to fill in missing fields
    if field_data:
        print(f"Using field data from form: {field_data}")
        # Use field_data for all fields (both existing and missing)
        for field in list(fields.keys()) + missing_fields:
            if field in field_data and field_data[field]:
                fields[field] = field_data[field]
                print(f"Setting field '{field}' with values: {field_data[field]}")
            elif field in missing_fields:
                # If a field is missing and not in field_data, use a default
                fields[field] = ["[No value provided]"]
                print(f"No value for missing field '{field}', using default")
    else:
        # This is for command-line usage - keep it for testing
        if missing_fields:
            for field in missing_fields:
                user_input = input(f"No sample data available for field '{field}'. Enter values (comma-separated): ")
                fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]

    # Generate all permutations
    permutations = generate_permutations(fields)
    print(f"Generated {len(permutations)} permutations")

    generated_stories_ids = []
    for permutation in permutations:
        story_content = template.content
        for field, value in zip(fields.keys(), permutation):
            story_content = story_content.replace(f"{{{field}}}", value)

        # Create and save the new story
        new_story = Story(content=story_content, template_id=template_id)
        db.session.add(new_story)
        db.session.flush()  # Use flush instead of commit to batch operations
        
        # Add category associations if provided
        if category_ids:
            for category_id in category_ids:
                try:
                    story_category = StoryCategory(story_id=new_story.story_id, category_id=category_id)
                    db.session.add(story_category)
                except Exception as e:
                    print(f"Error adding category {category_id} to story: {e}")
        
        generated_stories_ids.append(new_story.story_id)

    # One commit at the end is more efficient
    db.session.commit()
    print(f"Created {len(generated_stories_ids)} stories")
    return generated_stories_ids

def generate_stories(template_id, field_data, category_ids=None):
    """Generate stories from a template and field data, with optional categories"""
    template = db.session.query(Template).get(template_id)
    if not template:
        raise ValueError(f"Template with ID {template_id} not found")
    
    # Use the existing template_filler function with category support
    return template_filler(template, template_id, field_data, category_ids)

def generate_story_permutations(template_content, field_data):
    """Generate all possible story permutations from a template and field data."""
    # Extract field names from template
    field_names = re.findall(r'\{(.*?)\}', template_content)
    unique_field_names = list(set(field_names))
    
    # Ensure all required fields have values
    for field_name in unique_field_names:
        if field_name not in field_data or not field_data[field_name]:
            raise ValueError(f"Field '{field_name}' has no values assigned")
    
    # Generate all possible combinations of field values
    field_values_list = [field_data[field_name] for field_name in unique_field_names]
    combinations = list(itertools.product(*field_values_list))
    
    # Generate stories by substituting field values
    stories = []
    for combo in combinations:
        story = template_content
        for i, field_name in enumerate(unique_field_names):
            # Replace all occurrences of this field
            story = story.replace(f"{{{field_name}}}", str(combo[i]))
        stories.append(story)
    
    return stories

def update_field_words(field_data):
    """Update field words based on user selection"""
    for field_name, words in field_data.items():
        # Get or create the field
        field = db.session.query(Field).filter_by(field=field_name).first()
        if not field:
            field = Field(field=field_name)
            db.session.add(field)
            db.session.commit()
        
        # Clear existing relationships
        field.words = []
        
        # Add selected words
        for word in words:
            existing_word = db.session.query(Word).filter_by(word=word).first()
            if not existing_word:
                new_word = Word(word=word)
                field.words.append(new_word)
                db.session.add(new_word)
            else:
                field.words.append(existing_word)
        
        db.session.commit()
    return True



# import itertools
# import re
# import time
# from app import db
# from app.models import Template, Story, Question, Word, Field
# import llm as llm

# def get_all_templates():
#     return db.session.query(Template).all()

# def generate_stories(template_id, field_data, category_ids=None):
#     """Generate stories from a template and field data, with optional categories"""
#     template = db.session.query(Template).get(template_id)
#     if not template:
#         raise ValueError(f"Template with ID {template_id} not found")
    
#     # Generate story content
#     stories_content = generate_story_permutations(template.content, field_data)
    
#     # Add stories to the database with categories
#     story_ids = []
#     for content in stories_content:
#         # Add the story to get its ID
#         story = Story(content=content)
#         db.session.add(story)
#         db.session.flush()  # Get the ID before committing
        
#         # Add category associations if provided
#         if category_ids:
#             for category_id in category_ids:
#                 story_category = StoryCategory(story_id=story.story_id, category_id=category_id)
#                 db.session.add(story_category)
        
#         story_ids.append(story.story_id)
    
#     db.session.commit()
#     return story_ids

# def get_template_fields(template_id):
#     template = db.session.query(Template).get(template_id)
#     field_names = re.findall(r'\{(.*?)\}', template.content)
#     fields = {}
#     missing_fields = []
#     for field_name in field_names:
#         field = db.session.query(Field).filter_by(field=field_name).first()
#         if field:
#             words = [word.word for word in field.words]
#             fields[field_name] = words
#         else:
#             missing_fields.append(field_name)
#     return fields, missing_fields

# def add_words_to_field(field_name, new_words):
#     field = db.session.query(Field).filter_by(field=field_name).first()
#     if not field:
#         field = Field(field=field_name)
#         db.session.add(field)
#         db.session.commit()
#     words = [word.strip() for word in new_words.split(',')]
#     for word in words:
#         existing_word = db.session.query(Word).filter_by(word=word).first()
#         if not existing_word:
#             new_word = Word(word=word)
#             field.words.append(new_word)
#             db.session.add(new_word)
#         else:
#             if field not in existing_word.fields:
#                 existing_word.fields.append(field)
#     db.session.commit()

# def generate_permutations(fields):
#     """Generate all possible permutations of field values."""
#     field_names = list(fields.keys())
#     return list(itertools.product(*(fields[field] for field in field_names)))

# def template_filler(template, template_id, field_data=None):
#     """Fill the template with permutations of field values."""
#     fields, missing_fields = get_template_fields(template_id)
    
#     # If field_data is provided from the form, use it to fill in missing fields
#     if field_data:
#         print(f"Using field data from form: {field_data}")
#         # Use field_data for all fields (both existing and missing)
#         for field in list(fields.keys()) + missing_fields:
#             if field in field_data and field_data[field]:
#                 fields[field] = field_data[field]
#                 print(f"Setting field '{field}' with values: {field_data[field]}")
#             elif field in missing_fields:
#                 # If a field is missing and not in field_data, use a default
#                 fields[field] = ["[No value provided]"]
#                 print(f"No value for missing field '{field}', using default")
#     else:
#         # This is for command-line usage - keep it for testing
#         if missing_fields:
#             for field in missing_fields:
#                 user_input = input(f"No sample data available for field '{field}'. Enter values (comma-separated): ")
#                 fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]

#     # Generate all permutations
#     permutations = generate_permutations(fields)
#     print(f"Generated {len(permutations)} permutations")

#     generated_stories_ids = []
#     for permutation in permutations:
#         story_content = template.content
#         for field, value in zip(fields.keys(), permutation):
#             story_content = story_content.replace(f"{{{field}}}", value)

#         # Create and save the new story
#         new_story = Story(content=story_content, template_id=template_id)
#         db.session.add(new_story)
#         db.session.commit()  # Commit after each story to get the ID
#         generated_stories_ids.append(new_story.story_id)

#     print(f"Created {len(generated_stories_ids)} stories")
#     return generated_stories_ids

# def update_field_words(field_data):
#     """Update field words based on user selection"""
#     for field_name, words in field_data.items():
#         # Get or create the field
#         field = db.session.query(Field).filter_by(field=field_name).first()
#         if not field:
#             field = Field(field=field_name)
#             db.session.add(field)
#             db.session.commit()
        
#         # Clear existing relationships
#         field.words = []
        
#         # Add selected words
#         for word in words:
#             existing_word = db.session.query(Word).filter_by(word=word).first()
#             if not existing_word:
#                 new_word = Word(word=word)
#                 field.words.append(new_word)
#                 db.session.add(new_word)
#             else:
#                 field.words.append(existing_word)
        
#         db.session.commit()
#     return True

