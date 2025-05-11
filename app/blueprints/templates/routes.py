from flask import flash, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy import select
from ... import db
from ...services import  story_builder_service,  category_service, story_service
from ...models import  Story,  Word, Field, Template
from . import templates_bp
import json
from ...utils.pagination import Pagination

#Notes for self - check for duplication of retrieval of words etc from database. 
#I think maybe theres a mix/overlap between story_builder_service and routes etc

@templates_bp.route('/list')
def list():
    search_text = request.args.get('search_text', '')
    sort_by = request.args.get('sort_by', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # stmt = select(Template)
    # if search_text:
    #     stmt = stmt.where(Template.content.ilike(f'%{search_text}%'))
    # if sort_by == 'asc':
    #     stmt = stmt.order_by(Template.template_id.asc())
    # else:
    #     stmt = stmt.order_by(Template.template_id.desc())

    all_templates = story_builder_service.get_templates_filtered(search_text, sort_by)
    total = len(all_templates)
    start = (page - 1) * per_page
    end = start + per_page
    templates = all_templates[start:end]
    pagination = Pagination(templates, page, per_page, total)

    template_fields = story_builder_service.get_all_field_names()
    selected_template_ids = session.get('template_ids', [])

    return render_template(
        'see_all_templates.html',
        templates=templates,
        pagination=pagination,
        sort_by=sort_by,
        template_fields=template_fields,
        selected_template_ids=selected_template_ids
    )

@templates_bp.route('/add', methods=['POST'])
def add():
    template_content = request.form.get('template_content')
    if template_content:
        story_builder_service.add_template(template_content)
    return redirect(url_for('templates.list'))

@templates_bp.route('/update_template_selection', methods=['POST'])
def update_template_selection():
    """AJAX endpoint to update template selection in session"""
    data = request.get_json()
    
    # Get the current selection from session
    selected_template_ids = session.get('template_ids', [])
    
    # Clear all selected templates
    if data.get('action') == 'clear_all':
        selected_template_ids = []
    
    # Select multiple templates at once (for batch operations)
    elif data.get('action') == 'select_multiple':
        template_ids = data.get('template_ids', [])
        for template_id in template_ids:
            if template_id not in selected_template_ids:
                selected_template_ids.append(template_id)
    
    # Handle individual toggle
    elif 'template_id' in data:
        template_id = str(data['template_id'])
        is_selected = data.get('selected', False)
        
        if is_selected and template_id not in selected_template_ids:
            selected_template_ids.append(template_id)
        elif not is_selected and template_id in selected_template_ids:
            selected_template_ids.remove(template_id)
    
    # Store updated selection in session
    session['template_ids'] = selected_template_ids
    
    return jsonify({
        'success': True,
        'selected_count': len(selected_template_ids),
        'selected_ids': selected_template_ids
    })

@templates_bp.route('/generate_stories', methods=['GET', 'POST'])
def generate_stories():
    if request.method == 'POST':
        # For form submissions (field updates, generation)
        template_id = request.form.get('template_id')

        if template_id:
            session['template_id'] = template_id

        print("Form data received:")
        print("generate button:", "generate" in request.form)
        print("update_fields button:", "update_fields" in request.form)
        print("template_id:", request.form.get('template_id'))
        print("field_data:", request.form.get('field_data'))
        
        # Check if we're updating the fields or generating stories
        if 'update_fields' in request.form:
            # Process field updates
            field_data = json.loads(request.form.get('field_data', '{}'))
            story_builder_service.update_field_words(field_data)
            flash('Fields updated successfully!', 'success')
            return redirect(url_for('templates.generate_stories'))
            
        elif 'generate' in request.form:
            # Generate stories with current fields
            try:
                # Parse the field data from the form
                field_data = json.loads(request.form.get('field_data', '{}'))
                story_builder_service.update_field_words(field_data)  # Save fields


                template_id = session.get('template_id')
                if not template_id:
                    flash('No template selected. Please select a template first.', 'danger')
                    return redirect(url_for('templates.generate_stories'))
                
                # Process categories - both existing and new ones
                category_ids = []
                
                # Process existing categories
                selected_categories = request.form.getlist('story_categories')
                for cat_id in selected_categories:
                    try:
                        category_ids.append(int(cat_id))
                    except ValueError:
                        # Not an int, so it's a new category name, will be handled below
                        pass

                # Process new categories (names)
                new_categories = request.form.getlist('new_categories')
                for new_cat in new_categories:
                    if new_cat.strip():
                        try:
                            cat_id = category_service.add_category(new_cat.strip())
                            category_ids.append(cat_id)
                        except Exception as e:
                            flash(f"Could not add category '{new_cat}': {str(e)}", "danger")                             
                
                # Pass the field data and category_ids to the generate_stories function
                generated_story_ids = story_builder_service.generate_stories(template_id, field_data, category_ids)
                session['generated_story_ids'] = generated_story_ids
                
                if category_ids:
                    flash(f'Stories generated successfully with {len(category_ids)} categories!', 'success')
                else:
                    flash('Stories generated successfully!', 'success')
                    
                return redirect(url_for('templates.display_generated_stories'))
            
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print the full error stack
                flash(f'Error generating stories: {str(e)}', 'danger')
                return redirect(url_for('templates.generate_stories'))
    
    # GET request - display the form
    templates = story_builder_service.get_all_templates()
    
    # Get template_id either session (by default) or if I've missed something, from the args for backwards compat
    template_id = session.get('template_id') or request.args.get('template_id')

    # Update session if template_id came from query params
    if request.args.get('template_id'):
        session['template_id'] = request.args.get('template_id')
    
    fields = {}
    missing_fields = []
    template = None
    
    if template_id:
        template = story_builder_service.get_template_by_id(template_id)
        fields, missing_fields = story_builder_service.get_template_fields(template_id)

        print("===== DEBUG INFO =====")
        print("Template ID:", template_id)
        print("Fields from database:", fields)
        for field_name, words in fields.items():
            print(f"Field '{field_name}' has {len(words)} words: {words[:5]}...")
        print("Missing fields:", missing_fields)
        print("======================")
    
    # Get all categories for the category selection
    categories = category_service.get_all_categories()
    
    return render_template(
        'generate_stories_drag_and_drop.html', 
        templates=templates, 
        selected_template_id=template_id,
        template=template, 
        fields=fields,
        missing_fields=missing_fields,
        categories=categories  
    )

@templates_bp.route('/display_generated_stories', methods=['GET'])
def display_generated_stories():
    # Convert to strings for consistency
    generated_story_ids = [str(story_id) for story_id in session.get('generated_story_ids', [])]
    session['story_ids'] = generated_story_ids
    
    # When querying, convert back to integers
    stories = [story_service.get_story_by_id(int(story_id)) for story_id in generated_story_ids]
    return render_template('display_generated_stories.html', stories=stories)

@templates_bp.route('/add_word', methods=['POST'])
def add_word():
    # Check if this is an AJAX request or a form submission
    is_ajax = request.headers.get('Content-Type') == 'application/json'
    
    if is_ajax:
        # Handle AJAX request (from JavaScript)
        data = request.get_json()
        field_name = data.get('field_name')
        new_words = data.get('new_words')
        
        if field_name and new_words:
            try:
                story_builder_service.add_words_to_field(field_name, new_words)
                return jsonify({'success': True, 'message': f'Word(s) added to {field_name}'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    else:
        # Handle form submission (from HTML form)
        field_name = request.form.get('field_name')
        new_words = request.form.get('new_words')
        template_id = request.form.get('template_id')
        
        if field_name and new_words:
            story_builder_service.add_words_to_field(field_name, new_words)
        
        return redirect(url_for('templates.generate_stories', template_id=template_id))

@templates_bp.route('/delete_word', methods=['POST'])
def delete_word():
    data = request.get_json()
    field_name = data.get('field_name')
    word = data.get('word')

    if field_name and word:
        try:
            print(f"Attempting to delete word '{word}' from field '{field_name}'")
            story_builder_service.delete_word_from_field(field_name, word)
            return jsonify({'success': True, 'message': f'Word "{word}" deleted from field "{field_name}".'})
        except Exception as e:
            import traceback
            print(f"ERROR deleting word '{word}' from field '{field_name}':")
            print(traceback.format_exc())  # This prints the full stack trace
            return jsonify({'success': False, 'message': str(e)}), 500
    return jsonify({'success': False, 'message': 'Invalid data provided.'}), 400
