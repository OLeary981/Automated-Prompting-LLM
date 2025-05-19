import asyncio
import json
import logging
import time
import uuid
from threading import Thread

from flask import Response as FlaskResponse
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ... import db
from ...models import Model, Prompt, Question, Response
from ...services import async_service, llm_service, question_service
from . import llm_bp

logger = logging.getLogger(__name__)



@llm_bp.route('/select_model', methods=['GET', 'POST'])
def select_model():    
    # Check for story IDs in session
    if not session.get('story_ids') and request.method == 'GET':
        flash('To continue, please select one or more stories first.', 'info')
        return redirect(url_for('stories.list'))
    
    # Check for question_id in session
    if not session.get('question_id') and request.method == 'GET':
        flash('Please select a question to ask about your stories.', 'info')
        return redirect(url_for('questions.list'))

    # --- Preserve previous parameters if present ---
    previous_parameters = session.get('parameters')

    # Clear job/session data except parameters
    for key in ['job_id', 'model_id', 'model', 'provider', 'response_ids']:
        session.pop(key, None)
    if previous_parameters:

        session['parameters'] = previous_parameters
        flash("Your previous parameter settings have been loaded. You can adjust them below.", "info")

    if request.method == 'POST':
        model_id = request.form.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        if model:
            logger.debug("Model found, setting model and provider in session")
            session['model_id'] = model_id
            session['model'] = model['name']
            session['provider'] = model['provider'] 
            logger.debug(session)
        return redirect(url_for('llm.select_parameters'))  # Updated to use llm blueprint
    else:
        models = llm_service.get_all_models()
        return render_template('select_model.html', models=models)

@llm_bp.route('/select_parameters', methods=['GET', 'POST'])
def select_parameters():
    # Check prerequisites
    if not session.get('model_id'):
        flash('Please select a model first', 'warning')
        return redirect(url_for('llm.select_model'))
    
    if request.method == 'POST':
        # Store only actual parameters, not run_description
        parameters = {param: request.form.get(param) for param in request.form if param != 'run_description'}
        session['parameters'] = parameters
        # Store run_description separately if needed
        session['run_description'] = request.form.get('run_description', '')[:255]
        return redirect(url_for('llm.loading'))
        
    # GET request - show parameter form
    model_id = session.get('model_id')
    saved_parameters = session.get('parameters', {})
    # Log parameter details for debugging
    for name, value in saved_parameters.items():
        logger.info(f"SAVED PARAM DEBUG: {name} = {value} (type: {type(value)})")
    # Use service to handle parameter logic
    parameters = llm_service.get_model_parameters(model_id, saved_parameters)
    # Log parameter details for debugging
    for name, details in parameters.items():
        logger.info(f"PARAM DEBUG: {name} | type: {details.get('type')} | default: {details.get('default')} | min: {details.get('min_value')} | max: {details.get('max_value')}")
    return render_template('select_parameters.html', parameters=parameters)

# Routes for the progress tracking system
@llm_bp.route('/loading')
def loading():
    """Show loading screen while waiting for LLM processing to complete"""
    job_id = session.get('job_id')
    logger.info(f"In the laoding route, with job: {job_id}")
    # If no job ID in session (or it's invalid), generate a new one
    if not job_id or job_id not in async_service.processing_jobs:
        # Extract necessary session data
        story_ids = [int(sid) for sid in session.get("story_ids", [])]
        question_id = int(session.get("question_id"))
        model_id = int(session.get("model_id"))
        parameters = session.get('parameters', {})
        run_description = request.form.get('run_description', '')[:254] 
        
        # Use the service to create a new job
        job_id = async_service.create_job(model_id, story_ids, question_id, parameters, run_description)
        session['job_id'] = job_id
        logger.debug(f"Created new job: {job_id} with {len(story_ids)} stories to process")
    else:
        # Job already exists (e.g., from rerun_prompts)
        # Just update the last activity timestamp
        async_service.processing_jobs[job_id]["last_activity"] = time.time()
        logger.debug(f"Using existing job: {job_id} with params: {async_service.processing_jobs[job_id].get('params', {})}")
    
    # Clean up old jobs using the service
    async_service.cleanup_old_jobs()
    
    return render_template('loading.html', job_id=job_id)




@llm_bp.route('/rerun_prompts', methods=['POST'])
def rerun_prompts():
    logger.info("In the rerun_prompts route")
    run_description = request.form.get('run_description', '')[:254]
    prompt_ids = session.get('prompt_ids', [])
    if not prompt_ids:
        flash('No prompts selected to rerun.', 'warning')
        return redirect(url_for('prompts.list'))

    try:
        int_prompt_ids = [int(pid) for pid in prompt_ids]
        prompts = [db.session.query(Prompt).get(pid) for pid in int_prompt_ids if db.session.query(Prompt).get(pid)]
        if not prompts:
            flash('Selected prompts not found.', 'warning')
            return redirect(url_for('prompts.list'))

        # Use the first prompt for shared fields
        first_prompt = prompts[0]
        story_ids = []
        prompts_data = []
        for prompt in prompts:
            if prompt.story_id not in story_ids:
                story_ids.append(prompt.story_id)
            prompts_data.append({
                'prompt_id': prompt.prompt_id,
                'model_id': prompt.model_id,
                'story_id': prompt.story_id,
                'question_id': prompt.question_id,
                'parameters': {
                    'temperature': prompt.temperature,
                    'max_tokens': prompt.max_tokens,
                    'top_p': prompt.top_p
                }
            })

        # Optionally update session for context
        session['model_id'] = first_prompt.model_id
        session['question_id'] = first_prompt.question_id
        session['story_ids'] = [str(sid) for sid in story_ids]

        # Create the job using the shared fields from the first prompt
        job_id = async_service.create_job(
            model_id=first_prompt.model_id,
            story_ids=story_ids,
            question_id=first_prompt.question_id,
            parameters={
                'temperature': first_prompt.temperature,
                'max_tokens': first_prompt.max_tokens,
                'top_p': first_prompt.top_p
            },
            prompts_data=prompts_data,
            run_description=run_description
        )
        session['job_id'] = job_id
        async_service.cleanup_old_jobs()
        return redirect(url_for('llm.loading'))

    except Exception as e:
        flash(f'Error setting up prompt rerun: {str(e)}', 'danger')
        return redirect(url_for('prompts.list'))


@llm_bp.route('/start_processing/<job_id>')
def start_processing(job_id):
    logger.info(f"In the start processing route, Starting processing for job: {job_id}")
    if job_id not in async_service.processing_jobs:
        return jsonify({"status": "error", "message": "Invalid job ID"}), 404
    
    job = async_service.processing_jobs[job_id]
    logger.info(f"Current job status: {job.get('status')}")
    
    # Check if we're overloaded
    if not async_service.can_start_new_job():
        job["status"] = "queued"
        return jsonify({"status": "queued", "message": "Your job is queued due to high server load"})
    
    params = job["params"]
    
    try:
        # Get the running event loop from the service
        loop = async_service.get_event_loop()
        logger.info(f"Got event loop: {loop}")
        
        # Create the app for the background task
        app = current_app._get_current_object()
        
        
        # Start processing in background - THIS PART IS MISSING OR INCOMPLETE
        task = asyncio.run_coroutine_threadsafe(
            async_service.process_llm_requests(
                app,
                job_id, 
                params["model_id"], 
                params["story_ids"], 
                params["question_id"], 
                params["parameters"]
            ),
            loop
        )
        logger.info(f"Created task: {task}")
        
        # Store the task in the job
        job["task"] = task
        job["status"] = "started"
        return jsonify({"status": "started"})
    except Exception as e:
        logger.error(f"Error starting processing: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update job with error info
        if job_id in async_service.processing_jobs:
            async_service.processing_jobs[job_id]["status"] = "error"
            async_service.processing_jobs[job_id]["error"] = f"Failed to start processing: {str(e)}"
        
        return jsonify({"status": "error", "message": str(e)}), 500
    
@llm_bp.route('/progress_stream/<job_id>')
def progress_stream(job_id):
    print(f"SSE connection requested for job: {job_id}")
    logger.info(f"In the progress_stream route for : {job_id}")
    if job_id not in async_service.processing_jobs:
        print(f"Job ID not found: {job_id}")
        return jsonify({"status": "error", "message": "Invalid job ID"}), 404
    
    def generate():
        print(f"Starting SSE generator for job: {job_id}")
        last_progress = -1
        timeout = time.time() + 300  # 5 minute maximum wait
        
        # Send an initial message to establish the connection
        initial_data = json.dumps({'status': 'connected', 'job_id': job_id})
        print(f"Sending initial SSE data: {initial_data}")
        yield f"data: {initial_data}\n\n"
        
        try:
            while job_id in async_service.processing_jobs:
                job = async_service.processing_jobs[job_id]
                current_progress = job.get("progress", 0)
                status = job.get("status", "initializing")
                
                # Update last activity timestamp
                job["last_activity"] = time.time()
                
                # Only send updates when there's a change or status update
                if current_progress != last_progress or status in ["completed", "error", "cancelled"]:
                    last_progress = current_progress
                    
                    # Prepare the response data
                    response_data = {
                        "status": status,
                        "progress": current_progress,
                    }
                    
                    # Add results if completed
                    if status == "completed":
                        results = job.get("results", {})
                        response_ids = [r.get('response_id') for r in results.values() 
                                      if r.get('response_id')]
                        response_data["response_ids"] = response_ids
                        
                        # Store response IDs in the job data instead of the session
                        job["response_ids"] = response_ids
                        
                        # Try to store in session but it will fail outside request context
                        try:
                            # This will fail with "name 'app' is not defined" - that's ok
                            # We'll use job["response_ids"] in the llm_response route
                            session['response_ids'] = response_ids
                        except Exception as e:
                            # If we can't write to session here, that's ok 
                            print(f"Note: Couldn't store response_ids in session: {str(e)}")

                    # Add error info if failed
                    elif status == "error":
                        response_data["error"] = job.get("error", "Unknown error")
                    
                    # Serialize to JSON and send
                    json_data = json.dumps(response_data)
                    print(f"Sending SSE update: {json_data}")
                    yield f"data: {json_data}\n\n"
                    
                    # Break the loop after completion, error, or cancellation
                    if status in ["completed", "error", "cancelled"]:
                        break
                else:
                    # Send a keep-alive comment
                    yield f": keepalive\n\n"  # Changed to just keepalive without timestamp
                
                # Check for timeout
                if time.time() > timeout:
                    timeout_data = json.dumps({'status': 'timeout', 'progress': current_progress})
                    print(f"SSE timeout: {timeout_data}")
                    yield f"data: {timeout_data}\n\n"
                    break
                    
                # Wait a bit before next update
                time.sleep(0.5)
        except Exception as e:
            print(f"Error in SSE stream: {str(e)}")
            import traceback
            traceback.print_exc()
            # Send an error message if something goes wrong
            error_data = json.dumps({'status': 'error', 'error': str(e)})
            print(f"SSE error: {error_data}")
            yield f"data: {error_data}\n\n"
    
    # Set the appropriate headers for SSE
    response = FlaskResponse(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@llm_bp.route('/cancel_processing/<job_id>')
def cancel_processing(job_id):
    if job_id in async_service.processing_jobs:
        # Mark job as cancelled
        async_service.processing_jobs[job_id]["status"] = "cancelled"
        async_service.processing_jobs[job_id]["processing"] = False
        
        # Clean up after a short delay
        def delayed_cleanup():
            time.sleep(5)
            if job_id in async_service.processing_jobs:
                del async_service.processing_jobs[job_id]
        
        Thread(target=delayed_cleanup, daemon=True).start()
        
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "error", "message": "Job not found"}), 404


