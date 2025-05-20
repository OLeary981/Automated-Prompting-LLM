import itertools
import re

from flask import abort
from sqlalchemy import select

from app import db
from app.models import Field, Story, StoryCategory, Template, Word

from ..services import story_service


def get_all_templates():
    return db.session.execute(select(Template)).scalars().all()

# def get_all_fields():
#     return db.session.query(Field.field).order_by(Field.field).all()

def get_all_field_names():
    stmt = select(Field.field).order_by(Field.field)
    return [f[0] for f in db.session.execute(stmt).all()]

def get_template_by_id(template_id):
    template = db.session.get(Template, template_id)
    if template is None:
        abort(404)
    return template

def get_templates_filtered(search_text='', sort_by='desc'):
    stmt = select(Template)
    if search_text:
        stmt = stmt.where(Template.content.ilike(f'%{search_text}%'))
    if sort_by == 'asc':
        stmt = stmt.order_by(Template.template_id.asc())
    else:
        stmt = stmt.order_by(Template.template_id.desc())
    return db.session.execute(stmt).scalars().all()

#Realised this was duplicated in the story_service.py file so deleted it. 
# def get_story_by_id(story_id):
#     return db.session.get(Story, story_id)

def add_template(content):
    """Add a new template to the database and return its ID."""
    new_template = Template(content=content)
    db.session.add(new_template)
    db.session.commit()
    return new_template.template_id

def get_template_fields(template_id):
    template = get_template_by_id( template_id)
    field_names = re.findall(r'\{(.*?)\}', template.content)
    fields = {}
    missing_fields = []
    for field_name in field_names:
        stmt = select(Field).filter_by(field=field_name)
        field = db.session.execute(stmt).scalars().first()
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
        stmt = select(Word).filter_by(word=word)
        existing_word = db.session.execute(stmt).scalars().first()
        if not existing_word:
            new_word = Word(word=word)
            field.words.append(new_word)
            db.session.add(new_word)
        else:
            if field not in existing_word.fields:
                existing_word.fields.append(field)
    db.session.commit()

def delete_word_from_field(field_name, word):
    """
    Remove a word from a field. If the word is not associated with any other fields,
    it will be deleted from the database entirely.
    
    Args:
        field_name (str): The name of the field
        word (str): The word to remove
        
    Returns:
        bool: True if successful
        
    Raises:
        ValueError: If the field or word is not found, or if the word is not associated with the field
    """
    # Find the field in the database
    field = db.session.query(Field).filter_by(field=field_name).first()
    if not field:
        raise ValueError(f"Field '{field_name}' not found.")

    # Find the word in the database
    word_entry = db.session.query(Word).filter_by(word=word).first()
    if not word_entry:
        raise ValueError(f"Word '{word}' not found.")
    
    # Check if the word is associated with the field
    if word_entry not in field.words:
        raise ValueError(f"Word '{word}' is not associated with field '{field_name}'.")
    
    # Remove the word from the field's collection
    field.words.remove(word_entry)
    
    # Check if the word is still associated with any fields
    remaining_fields = len(word_entry.fields)
    
    # If this was the last field association, delete the word entirely
    if remaining_fields == 0:
        print(f"Word '{word}' is no longer associated with any fields. Deleting it from the database.")
        db.session.delete(word_entry)
    else:
        print(f"Word '{word}' is still associated with {remaining_fields} other fields. Keeping it in the database.")
    
    # Commit the changes
    db.session.commit()
    
    print(f"Successfully removed word '{word}' from field '{field_name}'")
    return True

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
        # This is for command-line usage - testing
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
        
        story_id = story_service.add_story(story_content, category_ids, template_id)     
        
        generated_stories_ids.append(story_id)

    # One commit at the end is more efficient
    db.session.commit()
    print(f"Created {len(generated_stories_ids)} stories")
    return generated_stories_ids

def generate_stories(template_id, field_data, category_ids=None):
    """Generate stories from a template and field data, with optional categories"""
    template = get_template_by_id( template_id)
    #don't need code below as get_template_by_id handles it with 404
    # if not template:
    #     raise ValueError(f"Template with ID {template_id} not found")
    
    # Use the existing template_filler function with category support
    return template_filler(template, template_id, field_data, category_ids)


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
            stmt = select(Word).filter_by(word=word)
            existing_word = db.session.execute(stmt).scalars().first()
            if not existing_word:
                new_word = Word(word=word)
                field.words.append(new_word)
                db.session.add(new_word)
            else:
                field.words.append(existing_word)
        
        db.session.commit()
    return True
