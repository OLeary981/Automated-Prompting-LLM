import datetime
from flask import Blueprint, flash, render_template, request, redirect, url_for, session, jsonify, Response as FlaskResponse, send_file
from .. import db, create_app
from .services import story_service, question_service, story_builder_service, llm_service, category_service
from .models import Template, Story, Question, Model, Provider, Response, StoryCategory, Prompt, Field
import time
import json
import threading
from threading import Thread
import asyncio
import uuid
import csv
import io


@bp.route('/select_parameters', methods=['GET', 'POST'])
def select_parameters():
    if request.method == 'POST':
        # Store the selected parameters in the session
        parameters = {param: request.form.get(param) for param in request.form}
        session['parameters'] = parameters

        # Redirect to the loading page
        return redirect(url_for('main.loading'))
    
    else:
        model_id = session.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        parameters = model.parameters
        saved_parameters = session.get('parameters', {})
        
        # Check if we have saved parameters that match the current model's parameters
        # If so, use them instead of defaults
        if saved_parameters:
            print("Found saved parameters in session:", saved_parameters)
            # Create a new parameters dict with saved values where available
            for param_name, param_details in parameters.items():
                if param_name in saved_parameters:
                    # Convert the saved value to the appropriate type
                    saved_value = saved_parameters[param_name]
                    if param_details['type'] == 'float':
                        try:
                            saved_value = float(saved_value)
                            # Check if saved value is within allowed range
                            if saved_value >= param_details['min_value'] and saved_value <= param_details['max_value']:
                                param_details['default'] = saved_value
                        except (ValueError, TypeError):
                            # Invalid saved value, stick with the default
                            pass
                    elif param_details['type'] == 'int':
                        try:
                            saved_value = int(saved_value)
                            # Check if saved value is within allowed range
                            if saved_value >= param_details['min_value'] and saved_value <= param_details['max_value']:
                                param_details['default'] = saved_value
                        except (ValueError, TypeError):
                            # Invalid saved value, stick with the default
                            pass
        
        print("Using parameters:", parameters)
        return render_template('select_parameters.html', parameters=parameters)

def run_async_loop():
    global _event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with _event_loop_lock:
        _event_loop = loop  # Thread-safe assignment
    loop.run_forever()

# Helper to get the running event loop (from any thread)
def get_event_loop():
    global _event_loop
    with _event_loop_lock:
        if _event_loop is None:
            raise RuntimeError("Event loop not initialized")
        return _event_loop

# Start the background thread on module load
background_thread = Thread(target=run_async_loop, daemon=True)
background_thread.start()
time.sleep(0.1)  # Small delay to ensure the event loop initializes



# Add job rate limiting to prevent server overload
def can_start_new_job():
    """Check if we can start a new job based on current load"""
    # Count active jobs (those with processing=True and recent activity)
    current_time = time.time()
    active_jobs = 0
    for job in processing_jobs.values():
        if job.get("processing", False) and current_time - job.get("last_activity", 0) < 60:
            active_jobs += 1
    
    # Limit to 5 concurrent jobs (adjust based on your server capacity)
    return active_jobs < 5

# Main processing function that will run in the background asyncio loop
async def process_llm_requests(job_id, model_id=None, story_ids=None, question_id=None, parameters=None):
    app = create_app()
    with app.app_context():
        job = processing_jobs[job_id]
        
        # Check if this is a rerun job
        is_rerun = False
        prompts_data = None
        
        if 'params' in job and job['params'].get('is_rerun'):
            is_rerun = True
            prompts_data = job['params'].get('prompts_data', [])
            job["total"] = len(prompts_data)
        else:
            # Standard processing
            job["total"] = len(story_ids)
        
        job["status"] = "running"
        job["completed"] = 0
        job["results"] = {}
        
        try:
            if is_rerun:
                # Process each prompt
                for i, prompt_data in enumerate(prompts_data):
                    # Check if job has been cancelled
                    if job_id not in processing_jobs:
                        return
                    
                    # Get the prompt data
                    prompt_id = prompt_data['prompt_id']
                    model_id = prompt_data['model_id']
                    story_id = prompt_data['story_id']
                    question_id = prompt_data['question_id']
                    parameters = prompt_data['parameters']
                    
                    # Call the LLM service for this prompt
                    try:
                        # Get the story, question, and model details
                        story = llm_service.get_story_by_id(story_id)
                        question = llm_service.get_question_by_id(question_id)
                        provider_name = llm_service.get_provider_name_by_model_id(model_id)
                        model_name = llm_service.get_model_name_by_id(model_id)
                        
                        # Simulate API rate limiting delay
                        request_delay = llm_service.get_request_delay_by_model_id(model_id)
                        if i > 0 and request_delay > 0:
                            await asyncio.sleep(request_delay)
                        
                        # Make the actual API call (non-async)
                        def call_llm_with_context():
                            with app.app_context():
                                return llm_service.call_llm(
                                    provider_name, 
                                    story.content, 
                                    question.content, 
                                    story_id, 
                                    question_id, 
                                    model_name, 
                                    model_id, 
                                    rerun_from_prompt_id=prompt_id,
                                    **parameters
                                )
                        
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(None, call_llm_with_context)
                        
                        # Update job state
                        job["completed"] += 1
                        if response:
                            if isinstance(response, dict) and "response_id" in response:
                                job["results"][prompt_id] = {'response_id': response["response_id"]}
                            elif hasattr(response, 'response_id'):
                                job["results"][prompt_id] = {'response_id': response.response_id}
                            else:
                                print(f"Warning: Unexpected response format: {type(response)}")
                                job["results"][prompt_id] = {'error': 'Invalid response format'}
                    except Exception as e:
                        print(f"Error processing prompt {prompt_id}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        job["results"][prompt_id] = {'error': str(e)}
                    
                    # Calculate and update progress percentage
                    progress = int((job["completed"] / job["total"]) * 100)
                    job["progress"] = progress
                    job["last_activity"] = time.time()
            else:
                # Original story-by-story processing
                for i, story_id in enumerate(story_ids):
                    if job_id not in processing_jobs:
                        return
                        
                    try:
                        # Get story content
                        story = llm_service.get_story_by_id(story_id)
                        question = llm_service.get_question_by_id(question_id)
                        provider_name = llm_service.get_provider_name_by_model_id(model_id)
                        model_name = llm_service.get_model_name_by_id(model_id)
                        
                        # Simulate API rate limiting delay
                        request_delay = llm_service.get_request_delay_by_model_id(model_id)
                        if i > 0 and request_delay > 0:
                            await asyncio.sleep(request_delay)
                        
                        # Make the actual API call (non-async)
                        def call_llm_with_context():
                            with app.app_context():
                                return llm_service.call_llm(
                                    provider_name, 
                                    story.content, 
                                    question.content, 
                                    story_id, 
                                    question_id, 
                                    model_name, 
                                    model_id,
                                    **parameters
                                )
                        
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(None, call_llm_with_context)
                        
                        # Update job state
                        job["completed"] += 1
                        if response:
                            if isinstance(response, dict) and "response_id" in response:
                                job["results"][story_id] = {'response_id': response["response_id"]}
                            elif hasattr(response, 'response_id'):
                                job["results"][story_id] = {'response_id': response.response_id}
                            else:
                                print(f"Warning: Unexpected response format: {type(response)}")
                                job["results"][story_id] = {'error': 'Invalid response format'}
                    except Exception as e:
                        print(f"Error processing story {story_id}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        job["results"][story_id] = {'error': str(e)}
                    
                    # Calculate and update progress percentage
                    progress = int((job["completed"] / job["total"]) * 100)
                    job["progress"] = progress
                    job["last_activity"] = time.time()
            
            # Mark job as completed
            job["status"] = "completed"
            job["progress"] = 100
            
            # Keep the results in memory for a few minutes
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            print(f"Error in LLM processing: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Update job with error info
            job["status"] = "error"
            job["error"] = str(e)
            
        finally:
            # Clean up if job still exists
            if job_id in processing_jobs:
                # Don't delete yet, just mark status
                job["processing"] = False

def cleanup_old_jobs():
    """Clean up old jobs that are no longer needed to prevent memory leaks"""
    current_time = time.time()
    jobs_to_remove = []
    
    for job_id, job in processing_jobs.items():
        # Clean up completed jobs older than 30 minutes
        if job.get("status") in ["completed", "error", "cancelled"]:
            if current_time - job.get("last_activity", 0) > 1800:  # 30 minutes
                jobs_to_remove.append(job_id)
        
        # Clean up stalled jobs (no activity for 2 hours)
        elif current_time - job.get("last_activity", 0) > 7200:  # 2 hours
            jobs_to_remove.append(job_id)
    
    # Remove the jobs
    for job_id in jobs_to_remove:
        if job_id in processing_jobs:
            print(f"Cleaning up old job: {job_id}")
            del processing_jobs[job_id]

# Routes for the progress tracking system
@bp.route('/loading')
def loading():
    # Generate unique job ID for this processing request
    job_id = str(uuid.uuid4())
    
    # Extract necessary session data
    model_id = session.get('model_id')
    story_ids = session.get('story_ids', [])
    question_id = session.get('question_id')
    parameters = session.get('parameters', {})
    
    # Store job ID in session
    session['job_id'] = job_id
    
    # Initialize job tracking
    processing_jobs[job_id] = {
        "status": "initializing",
        "progress": 0,
        "total": len(story_ids),
        "completed": 0,
        "results": {},
        "processing": True,
        "last_activity": time.time(),
        # Store parameters for reference
        "params": {
            "model_id": model_id,
            "story_ids": story_ids,
            "question_id": question_id,
            "parameters": parameters
        }
    }
    
    # Clean up old jobs
    cleanup_old_jobs()    
    return render_template('loading.html', job_id=job_id)



# Update start_processing to include rate limiting
@bp.route('/start_processing/<job_id>')
def start_processing(job_id):
    if job_id not in processing_jobs:
        return jsonify({"status": "error", "message": "Invalid job ID"}), 404
    
    job = processing_jobs[job_id]
    
    # Check if we're overloaded
    if not can_start_new_job():
        job["status"] = "queued"
        return jsonify({"status": "queued", "message": "Your job is queued due to high server load"})
    
    params = job["params"]
    
    try:
        # Get the running event loop
        loop = get_event_loop()
        
        # Start processing in background
        task = asyncio.run_coroutine_threadsafe(
            process_llm_requests(
                job_id, 
                params["model_id"], 
                params["story_ids"], 
                params["question_id"], 
                params["parameters"]
            ),
            loop
        )
        
        job["task"] = task
        job["status"] = "started"


        return jsonify({"status": "started"})
    
    except Exception as e:
        print(f"Error starting processing: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update job with error info
        if job_id in processing_jobs:
            processing_jobs[job_id]["status"] = "error"
            processing_jobs[job_id]["error"] = f"Failed to start processing: {str(e)}"
        
        return jsonify({"status": "error", "message": str(e)}), 500
    
@bp.route('/progress_stream/<job_id>')
def progress_stream(job_id):
    print(f"SSE connection requested for job: {job_id}")
    if job_id not in processing_jobs:
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
            while job_id in processing_jobs:
                job = processing_jobs[job_id]
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


@bp.route('/cancel_processing/<job_id>')
def cancel_processing(job_id):
    if job_id in processing_jobs:
        # Mark job as cancelled
        processing_jobs[job_id]["status"] = "cancelled"
        processing_jobs[job_id]["processing"] = False
        
        # Clean up after a short delay
        def delayed_cleanup():
            time.sleep(5)
            if job_id in processing_jobs:
                del processing_jobs[job_id]
        
        Thread(target=delayed_cleanup, daemon=True).start()
        
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "error", "message": "Job not found"}), 404

#possibly not needed now
@bp.route('/progress')
def progress_legacy():
    job_id = session.get('job_id')
    if not job_id or job_id not in processing_jobs:
        return jsonify({"error": "No active job found"}), 404
    
    # Redirect to the new progress stream
    return redirect(url_for('main.progress_stream', job_id=job_id))

@bp.route('/rerun_prompts', methods=['POST'])
def rerun_prompts():
    """Endpoint to rerun selected prompts"""
    # Get selected prompt IDs from session
    prompt_ids = session.get('prompt_ids', [])
    
    if not prompt_ids:
        flash('No prompts selected to rerun.', 'warning')
        return redirect(url_for('main.see_all_prompts'))
    
    # Create a new job for rerunning these prompts
    job_id = str(uuid.uuid4())
    
    try:
        # Collect all the data needed for rerunning
        prompts_data = []
        for prompt_id in prompt_ids:
            prompt = db.session.query(Prompt).get(int(prompt_id))
            if prompt:
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
        
        if not prompts_data:
            flash('No valid prompts found to rerun.', 'warning')
            return redirect(url_for('main.see_all_prompts'))
            
        # Store job info
        processing_jobs[job_id] = {
            "status": "initializing",
            "progress": 0,
            "total": len(prompts_data),
            "completed": 0,
            "results": {},
            "processing": True,
            "last_activity": time.time(),
            "params": {
                "prompts_data": prompts_data,
                "is_rerun": True
            }
        }
        
        # Store job ID in session
        session['job_id'] = job_id
        
        # Clean up old jobs
        cleanup_old_jobs()
        
        return redirect(url_for('main.loading'))
        
    except Exception as e:
        flash(f'Error setting up prompt rerun: {str(e)}', 'danger')
        return redirect(url_for('main.see_all_prompts'))


@bp.route('/llm_response', methods=['GET', 'POST'])
def llm_response():
    if request.method == 'POST':
        print("POST request received on llm_response")
        # Process form data
        response_id = request.form.get('response_id')
        print(f"Response ID from form: {response_id}")
        
        if response_id:
            flagged_for_review = f'flagged_for_review_{response_id}' in request.form
            review_notes = request.form.get(f'review_notes_{response_id}', '')
            
            print(f"Flagged for review: {flagged_for_review}")
            print(f"Review notes: {review_notes}")

            try:
                # Get the response
                response = db.session.query(Response).get(response_id)
                if response:
                    print(f"Found response {response_id} in database")
                    # Update the fields
                    response.flagged_for_review = flagged_for_review
                    response.review_notes = review_notes
                    
                    # Simpler transaction handling - just commit the change
                    db.session.commit()
                    
                    print(f"Successfully updated response {response_id}")
                    flash(f'Response {response_id} updated successfully!', 'success')
                else:
                    print(f"Response {response_id} not found in database")
                    flash(f'Error: Response {response_id} not found.', 'danger')
            except Exception as e:
                print(f"Error updating response: {str(e)}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                flash(f'Error updating response: {str(e)}', 'danger')

        return redirect(url_for('main.llm_response'))

    # Get job_id from the session
    job_id = session.get('job_id')
    
    # Try to get response_ids from the job data first
    response_ids = []
    if job_id and job_id in processing_jobs:
        # Get from job data
        job = processing_jobs[job_id]
        response_ids = job.get("response_ids", [])
        
        # If we found response IDs, store them in the session for future use
        # (especially after the job is cleaned up)
        if response_ids:
            session['response_ids'] = response_ids
    
    # If no response_ids found in job data, try session as fallback
    if not response_ids:
        response_ids = session.get('response_ids', [])
    
    print(f"Retrieved response_ids: {response_ids}")
    
    # Fetch stories
    story_ids = session.get('story_ids', [])
    stories = [db.session.query(Story).get(story_id) for story_id in story_ids]
    
    # Fetch responses
    responses = []
    for response_id in response_ids:
        response = db.session.query(Response).get(response_id)
        if response:
            responses.append(response)
    
    print(f"Found {len(responses)} responses")
    
    # If we have no responses but have story_ids, perhaps the responses weren't stored properly
    if not responses and story_ids:
        flash('No responses found for your stories. There might have been an issue with the LLM processing.', 'warning')
    
    response_details = []
    for response in responses:
        response_details.append({
            'response_id': response.response_id,
            'response_content': response.response_content,
            'flagged_for_review': response.flagged_for_review,
            'review_notes': response.review_notes
        })

    # Retrieve model, provider, and question
    question_id = session.get('question_id')
    question = db.session.query(Question).get(question_id).content if question_id else None

    return render_template('llm_response.html', 
                          combined_data=zip(stories, response_details),
                          model=session.get('model'), 
                          provider=session.get('provider'), 
                          question=question)