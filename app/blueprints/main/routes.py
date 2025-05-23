from flask import flash, render_template, request, redirect, url_for, session
from app.services import async_service
from . import main_bp



@main_bp.route('/')
def index():
    return render_template('index.html')




@main_bp.route('/clear_session', methods=['GET'])
def clear_session():

    # Get selective clearing parameters
    clear_model = request.args.get('clear_model') == 'true'
    clear_parameters = request.args.get('clear_parameters') == 'true'
    clear_stories = request.args.get('clear_stories') == 'true'
    clear_question = request.args.get('clear_question') == 'true'
    clear_all = 'clear_all' in request.args
    
    print("Session before clearing:", dict(session))
    
    if clear_all:
        # Current behavior - full clearing and job cancellation
        cleared_jobs = 0
        for job_id, job in list(async_service.processing_jobs.items()):
            try:
                # Cancel the task if it exists and is not done
                if "task" in job and hasattr(job["task"], "cancel") and not job["task"].done():
                    print(f"Canceling task for job {job_id}")
                    job["task"].cancel()
                    cleared_jobs += 1
                
                # Mark job as cancelled
                job["status"] = "cancelled"
                job["processing"] = False
            except Exception as e:
                print(f"Error canceling job {job_id}: {str(e)}")
        
        # Clear all processing jobs
        async_service.processing_jobs.clear()
        
        # Clear session data
        session.clear()
        
        flash(f'Session data cleared and {cleared_jobs} background tasks cancelled!', 'success')
        print(f"Cleared {cleared_jobs} tasks from processing_jobs")
    else:
        # Selective clearing of session data
        items_cleared = []
        stories_source = request.args.get('stories_source') == 'true'
        clear_templates = request.args.get('clear_templates') == 'true'

        if stories_source and 'stories_source' in session:
            session.pop('stories_source')
            session.pop('template_count', None)  # Also clear template_count
            items_cleared.append('template filter')

        if clear_templates and 'template_ids' in session:
            session.pop('template_ids')
            items_cleared.append('template selection')
        # Clear model and provider if requested
        if clear_model:
            model_keys = ['model', 'provider', 'model_id']
            cleared_any = False
            for key in model_keys:
                if key in session:
                    session.pop(key)
                    cleared_any = True
            # Only append if all three keys are now absent from the session
            if all(key not in session for key in model_keys) and cleared_any:
                items_cleared.append('model selection')
            
            
        
        if clear_parameters and 'parameters' in session:
            session.pop('parameters')
            items_cleared.append('parameters')
            
        if clear_stories and 'story_ids' in session:
            session.pop('story_ids')
            items_cleared.append('story selection')
            
        if clear_question:
            if 'question_id' in session:
                session.pop('question_id')
            if 'question_content' in session:
                session.pop('question_content')
                items_cleared.append('question')
            
        # Only show a flash message if something was cleared
        if items_cleared:
            flash(f'Cleared {", ".join(items_cleared)} from session', 'info')
        
       

        print("Session after selective clearing:", dict(session))
    
    # Get the redirect URL - either specified or default to index
    redirect_url = request.args.get('redirect_to', url_for('main.index'))
    return redirect(redirect_url)
   

