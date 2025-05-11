from flask import current_app, flash, render_template, request, redirect, url_for, session, jsonify
from ... import db
from ...services import story_service,  category_service
from ...models import  Story,  StoryCategory
from . import stories_bp


@stories_bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        content = request.form.get('story_content')
        new_category = request.form.get('new_category')
        selected_categories = request.form.getlist('categories')
        category_ids = [int(cat_id) for cat_id in selected_categories if cat_id]
        
        if content:
            try:
                story_id = story_service.add_story_with_categories(content, category_ids, new_category)
                flash('Story added successfully!', 'success')                
            except Exception as e:
                flash(f'Error adding story: {str(e)}', 'danger')                
        return redirect(url_for('stories.list'))
    
    categories = category_service.get_all_categories()
    return render_template('add_story.html', categories=categories)

@stories_bp.route('/list')
def list():
    # Get the search and filter parameters
    search_text = request.args.get('search_text', '')
    category_filter = request.args.get('category_filter', '')
    sort_by = request.args.get('sort_by', 'desc')  # Default to descending (newest first)
    
    # Check if we're filtering by templates (save source for template use)
    source = request.args.get('source')
    
    # Store template filter information consistently in session FIRST
    if source == 'templates':
        session['stories_source'] = 'templates'
        # Also set template_count if provided
        if request.args.get('template_count'):
            session['template_count'] = request.args.get('template_count')
    
    # THEN check if we're filtering by templates
    is_template_filtered = session.get('stories_source') == 'templates' and session.get('template_ids')
    
    # Get the current page from the request, default to page 1
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config["PER_PAGE"], type=int)

    # Start building the query
    query = db.session.query(Story).options(
        db.joinedload(Story.story_categories).joinedload(StoryCategory.category)
    )

    # Filter by templates if needed
    if is_template_filtered:
        template_ids = [int(tid) for tid in session.get('template_ids', [])]
        query = query.filter(Story.template_id.in_(template_ids))

    # Apply search filter if provided
    if search_text:
        query = query.filter(Story.content.ilike(f'%{search_text}%'))
    
    # Apply category filter if provided
    if category_filter:
        try:
            category_id = int(category_filter)
            query = query.join(StoryCategory).filter(StoryCategory.category_id == category_id)
        except (ValueError, TypeError):
            # Handle invalid category_filter value
            flash('Invalid category filter', 'warning')
    
    # Apply sorting based on the `id`
    if sort_by == 'asc':
        query = query.order_by(Story.story_id.asc())  # Oldest to most recent (lower ID first)
    else:
        query = query.order_by(Story.story_id.desc())  # Most recent to oldest (higher ID first)

    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    stories = pagination.items

    # Get all categories for the dropdown
    categories = category_service.get_all_categories()
    
    # Get currently selected story IDs from session
    selected_story_ids = session.get('story_ids', [])

    # Get the template count for display (either from request or session)
    template_count = session.get('template_count')
    
    # Render with explicit source parameters
    return render_template(
        'see_all_stories.html',
        stories=stories,
        categories=categories,
        pagination=pagination,
        sort_by=sort_by,
        selected_story_ids=selected_story_ids,
        is_template_filtered=is_template_filtered,
        template_count=template_count,
        source=session.get('stories_source')  # Use session value for consistency
    )
       

@stories_bp.route('/update_selection', methods=['POST'])
def update_selection():
    data = request.get_json()
    
    # Get the current selection from session
    selected_story_ids = session.get('story_ids', [])
    
    # Clear all selected stories
    if data.get('action') == 'clear_all':
        selected_story_ids = []
    
    # Select multiple stories at once (for batch operations)
    elif data.get('action') == 'select_multiple':
        story_ids = data.get('story_ids', [])
        for story_id in story_ids:
            if story_id not in selected_story_ids:
                selected_story_ids.append(story_id)
    
    # Handle individual toggle
    elif 'story_id' in data:
        story_id = str(data['story_id'])
        is_selected = data.get('selected', False)
        
        if is_selected and story_id not in selected_story_ids:
            selected_story_ids.append(story_id)
        elif not is_selected and story_id in selected_story_ids:
            selected_story_ids.remove(story_id)
    
    # Store updated selection in session
    session['story_ids'] = selected_story_ids
    
    return jsonify({
        'success': True,
        'selected_count': len(selected_story_ids),
        'selected_ids': selected_story_ids
    })

@stories_bp.route('/select', methods=['GET', 'POST'])
def select():
    if request.method == 'POST':
        if 'deselect_story_id' in request.form:
            # Deselect the story
            story_id = request.form.get('deselect_story_id')
            story_ids = session.get('story_ids', [])
            if story_id in story_ids:
                story_ids.remove(story_id)
            session['story_ids'] = story_ids
            print(session)
        else:
            # Select the story
            story_id = request.form.get('story_id')
            story = db.session.query(Story).filter_by(story_id=story_id).first()
            if story:
                story_ids = session.get('story_ids', [])
                if story_id not in story_ids:
                    story_ids.append(story_id)
                session['story_ids'] = story_ids
                print(session)
        return redirect(url_for('stories.select'))
    else:
        # GET request - check for mode parameter
        # mode = request.args.get('mode') - commented out as not used at the moment (testing if all still ok)
        story_ids = session.get('story_ids', [])
        
        # If mode=add or no stories selected, show the selection page
        # if mode == 'add' or not story_ids:
        if not story_ids:
            return redirect(url_for('stories.list'))
        else:
            # Otherwise show the selected stories
            selected_stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
            all_stories = story_service.get_all_stories()
            return render_template('selected_stories.html', selected_stories=selected_stories, all_stories=all_stories)

@stories_bp.route('/select_all_filtered', methods=['POST'])
def select_all_filtered():
    # Check if the request is AJAX
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Invalid request'}), 400
    
    # Get filter parameters from the request
    data = request.get_json()
    search_text = data.get('search_text', '')
    category_filter = data.get('category_filter', '')
    template_filter = data.get('template_filter', False)
    
    # Build the query (similar to see_all_stories but get only IDs)
    query = db.session.query(Story.story_id)
    
    # Apply template filter if active
    if template_filter and session.get('template_ids'):
        template_ids = [int(tid) for tid in session.get('template_ids', [])]
        query = query.filter(Story.template_id.in_(template_ids))
    
    # Apply search filter if provided
    if search_text:
        query = query.filter(Story.content.ilike(f'%{search_text}%'))
    
    # Apply category filter if provided
    if category_filter and category_filter.strip():
        try:
            category_id = int(category_filter)
            query = query.join(StoryCategory).filter(StoryCategory.category_id == category_id)
        except (ValueError, TypeError):
            # Invalid category_filter, ignore it
            pass
    
    # Get all story IDs that match the filters
    story_ids = [str(row.story_id) for row in query.all()]
    
    # Update session with these IDs
    session['story_ids'] = story_ids
    
    # Return the number of stories selected
    return jsonify({
        'success': True,
        'selected_count': len(story_ids),
        'selected_ids': story_ids
    })


@stories_bp.route('/view_template_stories')
def view_template_stories():
    """View all stories related to templates selected in session"""
    
    # Get template IDs from session
    template_ids = session.get('template_ids', [])
    
    if not template_ids:
        flash('No templates selected. Please select at least one template.', 'warning')
        return redirect(url_for('templates.list'))
    
    # Convert template IDs to integers for the database query
    int_template_ids = [int(tid) for tid in template_ids]
    
    # Get story count for these templates before redirecting
    stories_count = db.session.query(Story).filter(Story.template_id.in_(int_template_ids)).count()
    
    if stories_count == 0:
        flash('No stories found for the selected templates', 'info')
        return redirect(url_for('templates.list'))
    
    # Clear any previous story selection
    if 'story_ids' in session:
        session.pop('story_ids')
        
    # Store story info in session
    session['stories_source'] = 'templates'
    session['template_count'] = len(template_ids)
    
    # Generate template information for the flash message
    template_text = "1 template" if len(template_ids) == 1 else f"{len(template_ids)} templates"
    
    # Flash a message showing the filter is active
    flash(f'Showing {stories_count} stories from {template_text}', 'info')
    
    # Redirect to see_all_stories with a source parameter
    return redirect(url_for('stories.list', 
                          source='templates',
                          template_count=len(template_ids)))

@stories_bp.route('/manage_categories', methods=['GET', 'POST'])
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            category_name = request.form.get('category_name')
            if category_name and category_name.strip():
                try:
                    category_service.add_category(category_name.strip())
                    flash(f'Category "{category_name}" added successfully!', 'success')
                except Exception as e:
                    flash(f'Error adding category: {str(e)}', 'danger')
        
        # Could add edit/delete functionality here
        
        return redirect(url_for('stories.manage_categories'))
    
    categories = category_service.get_all_categories()
    return render_template('manage_categories.html', categories=categories)