from flask import flash, render_template, request, redirect, url_for, session, jsonify, Response as FlaskResponse, current_app
from ...services import  question_service, llm_service, async_service
from . import llm_bp
from ...models import Response, Prompt, Model, Question
import logging
import time
from ... import db
import json
import asyncio
import uuid
from threading import Thread

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

    if request.method == 'POST':
        model_id = request.form.get('model_id')
        model = llm_service.get_model_by_id(model_id)
        if model:
            logger.debug("Model found, setting model and provider in session")
            session['model_id'] = model_id
            session['model'] = model.name
            session['provider'] = model.provider.provider_name
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
        # Store the selected parameters in the session
        parameters = {param: request.form.get(param) for param in request.form}
        session['parameters'] = parameters
        return redirect(url_for('llm.loading'))
    
    # GET request - show parameter form
    model_id = session.get('model_id')
    saved_parameters = session.get('parameters', {})
    
    # Use service to handle parameter logic
    parameters = llm_service.get_model_parameters(model_id, saved_parameters)
    
    return render_template('select_parameters.html', parameters=parameters)

# Routes for the progress tracking system
@llm_bp.route('/loading')
def loading():
    """Show loading screen while waiting for LLM processing to complete"""
    job_id = session.get('job_id')
    
    # If no job ID in session (or it's invalid), generate a new one
    if not job_id or job_id not in async_service.processing_jobs:
        # Extract necessary session data
        model_id = session.get('model_id')
        story_ids = session.get('story_ids', [])
        question_id = session.get('question_id')
        parameters = session.get('parameters', {})
        
        # Use the service to create a new job
        job_id = async_service.create_job(model_id, story_ids, question_id, parameters)
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



# Add job rate limiting to prevent server overload
# def can_start_new_job():
#     """Check if we can start a new job based on current load"""
#     # Count active jobs (those with processing=True and recent activity)
#     current_time = time.time()
#     active_jobs = 0
#     for job in processing_jobs.values():
#         if job.get("processing", False) and current_time - job.get("last_activity", 0) < 60:
#             active_jobs += 1
    
#     # Limit to 5 concurrent jobs (adjust based on your server capacity)
#     return active_jobs < 5

# # Main processing function that will run in the background asyncio loop
# async def process_llm_requests(job_id, model_id=None, story_ids=None, question_id=None, parameters=None):
#     app = create_app()
#     with app.app_context():
#         job = processing_jobs[job_id]
        
#         # Initialize job status
#         job["status"] = "running"
#         job["completed"] = 0
#         job["results"] = {}
        
#         try:
#             # Check if this is a rerun job
#             is_rerun = job.get("params", {}).get("is_rerun", False)
#             prompts_data = job.get("params", {}).get("prompts_data", [])
            
#             if is_rerun and prompts_data:
#                 # Process each prompt for rerun
#                 for i, prompt_data in enumerate(prompts_data):
                    
#                     # Check if job has been cancelled
#                     if job_id not in processing_jobs:
#                         return
                    
#                     # Get the prompt data
#                     prompt_id = prompt_data['prompt_id']
#                     model_id = prompt_data['model_id']
#                     story_id = prompt_data['story_id']
#                     question_id = prompt_data['question_id']
#                     parameters = prompt_data['parameters']
#                     print(f"Reusing prompt_id: {prompt_id} (type: {type(prompt_id)})")
#                     try:
#                         # Get the story, question, and model details
#                         story = llm_service.get_story_by_id(story_id)
#                         question = llm_service.get_question_by_id(question_id)
#                         provider_name = llm_service.get_provider_name_by_model_id(model_id)
#                         model_name = llm_service.get_model_name_by_id(model_id)
                        
#                         # Simulate API rate limiting delay
#                         request_delay = llm_service.get_request_delay_by_model_id(model_id)
#                         if i > 0 and request_delay > 0:
#                             await asyncio.sleep(request_delay)
                        
#                         # Make the actual API call (non-async)
#                         def call_llm_with_context():
#                             with app.app_context():
#                                 print(f"In async line 671 {prompt_id} (type: {type(prompt_id)})")
#                                 return llm_service.call_llm(
#                                     provider_name, 
#                                     story.content, 
#                                     question.content, 
#                                     story_id, 
#                                     question_id, 
#                                     model_name, 
#                                     model_id,
#                                     prompt_id=prompt_id,  # Important: Use prompt_id correctly
#                                     temperature=parameters['temperature'],  # Pass parameters explicitly
#                                     max_tokens=parameters['max_tokens'],
#                                     top_p=parameters['top_p']
#                                 )
                        
#                         loop = asyncio.get_running_loop()
#                         response = await loop.run_in_executor(None, call_llm_with_context)
                        
#                         # Update job state
#                         job["completed"] += 1
#                         if response:
#                             if isinstance(response, dict) and "response_id" in response:
#                                 job["results"][prompt_id] = {'response_id': response["response_id"]}
#                             elif hasattr(response, 'response_id'):
#                                 job["results"][prompt_id] = {'response_id': response.response_id}
#                             else:
#                                 print(f"Warning: Unexpected response format: {type(response)}")
#                                 job["results"][prompt_id] = {'error': 'Invalid response format'}
#                     except Exception as e:
#                         print(f"Error processing prompt {prompt_id}: {str(e)}")
#                         import traceback
#                         traceback.print_exc()
#                         job["results"][prompt_id] = {'error': str(e)}
                    
#                     # Calculate and update progress percentage
#                     progress = int((job["completed"] / job["total"]) * 100)
#                     job["progress"] = progress
#                     job["last_activity"] = time.time()
#             else:
#                 # Original story-by-story processing
#                 for i, story_id in enumerate(story_ids):
#                     if job_id not in processing_jobs:
#                         return
                        
#                     try:
#                         # Get story content
#                         story = llm_service.get_story_by_id(story_id)
#                         question = llm_service.get_question_by_id(question_id)
#                         provider_name = llm_service.get_provider_name_by_model_id(model_id)
#                         model_name = llm_service.get_model_name_by_id(model_id)
                        
#                         # Simulate API rate limiting delay
#                         request_delay = llm_service.get_request_delay_by_model_id(model_id)
#                         if i > 0 and request_delay > 0:
#                             await asyncio.sleep(request_delay)
                        
#                         # Make the actual API call (non-async)
#                         def call_llm_with_context():
#                             with app.app_context():
#                                 return llm_service.call_llm(
#                                     provider_name, 
#                                     story.content, 
#                                     question.content, 
#                                     story_id, 
#                                     question_id, 
#                                     model_name, 
#                                     model_id,
#                                     **parameters
#                                 )
                        
#                         loop = asyncio.get_running_loop()
#                         response = await loop.run_in_executor(None, call_llm_with_context)
                        
#                         # Update job state
#                         job["completed"] += 1
#                         if response:
#                             if isinstance(response, dict) and "response_id" in response:
#                                 job["results"][story_id] = {'response_id': response["response_id"]}
#                             elif hasattr(response, 'response_id'):
#                                 job["results"][story_id] = {'response_id': response.response_id}
#                             else:
#                                 print(f"Warning: Unexpected response format: {type(response)}")
#                                 job["results"][story_id] = {'error': 'Invalid response format'}
#                     except Exception as e:
#                         print(f"Error processing story {story_id}: {str(e)}")
#                         import traceback
#                         traceback.print_exc()
#                         job["results"][story_id] = {'error': str(e)}
                    
#                     # Calculate and update progress percentage
#                     progress = int((job["completed"] / job["total"]) * 100)
#                     job["progress"] = progress
#                     job["last_activity"] = time.time()
            
#             # Extract all response IDs from results and store in a consistent place
#             response_ids = []
#             for result_data in job["results"].values():
#                 if isinstance(result_data, dict) and "response_id" in result_data:
#                     response_ids.append(str(result_data["response_id"]))

#             # Store response IDs in the job in a standard way
#             job["response_ids"] = response_ids

#             # Mark job as completed
#             job["status"] = "completed"
#             job["progress"] = 100
            
#             # Keep the results in memory for a few minutes
#             await asyncio.sleep(300)  # 5 minutes
            
#         except Exception as e:
#             print(f"Error in LLM processing: {str(e)}")
#             import traceback
#             traceback.print_exc()
            
#             # Update job with error info
#             job["status"] = "error"
#             job["error"] = str(e)
            
#         finally:
#             # Clean up if job still exists
#             if job_id in processing_jobs:
#                 # Don't delete yet, just mark status
#                 job["processing"] = False

# def cleanup_old_jobs():
#     """Clean up old jobs that are no longer needed to prevent memory leaks"""
#     current_time = time.time()
#     jobs_to_remove = []
    
#     for job_id, job in processing_jobs.items():
#         # Clean up completed jobs older than 30 minutes
#         if job.get("status") in ["completed", "error", "cancelled"]:
#             if current_time - job.get("last_activity", 0) > 1800:  # 30 minutes
#                 jobs_to_remove.append(job_id)
        
#         # Clean up stalled jobs (no activity for 2 hours)
#         elif current_time - job.get("last_activity", 0) > 7200:  # 2 hours
#             jobs_to_remove.append(job_id)
    
#     # Remove the jobs
#     for job_id in jobs_to_remove:
#         if job_id in processing_jobs:
#             print(f"Cleaning up old job: {job_id}")
#             del processing_jobs[job_id]



@llm_bp.route('/start_processing/<job_id>')
def start_processing(job_id):
    logger.info(f"Starting processing for job: {job_id}")
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

#possibly not needed now
# @main_bp.route('/progress')
# def progress_legacy():
#     job_id = session.get('job_id')
#     if not job_id or job_id not in processing_jobs:
#         return jsonify({"error": "No active job found"}), 404
    
#     # Redirect to the new progress stream
#     return redirect(url_for('main.progress_stream', job_id=job_id))

@llm_bp.route('/rerun_prompts', methods=['POST'])
def rerun_prompts():
    """Endpoint to rerun selected prompts"""
    # Get selected prompt IDs from session
    print("==== RERUN PROMPTS CALLED ====")
    
    # Get selected prompt IDs from session
    prompt_ids = session.get('prompt_ids', [])
    print(f"Prompt IDs in session: {prompt_ids}")
    
    if not prompt_ids:
        print("No prompts selected to rerun.")
        flash('No prompts selected to rerun.', 'warning')
        return redirect(url_for('main.see_all_prompts'))
    
    # Create a new job for rerunning these prompts
    job_id = str(uuid.uuid4())
    print(f"Created rerun job ID: {job_id}")
    
    try:
        int_prompt_ids = [int(pid) for pid in prompt_ids]
        
        # Clear any existing response IDs to avoid showing old responses
        if 'response_ids' in session:
            session.pop('response_ids')
            
        # Collect all the data needed for rerunning
        prompts_data = []
        
        # Process only the first prompt to get model/question data (all prompts must share this)
        first_prompt = db.session.query(Prompt).get(int_prompt_ids[0])
        if not first_prompt:
            flash('Selected prompt not found.', 'warning')
            return redirect(url_for('main.see_all_prompts'))

        # Get model and provider info for display context
        model = db.session.query(Model).get(first_prompt.model_id)
        if model:
            session['model_id'] = model.model_id
            session['model'] = model.name
            session['provider'] = model.provider.provider_name
        
        # Set question ID for context
        session['question_id'] = first_prompt.question_id
        
        # Collect all story IDs
        story_ids = []
        
        for prompt_id in int_prompt_ids:
            prompt = db.session.query(Prompt).get(prompt_id)
            if prompt:
                if prompt.story_id not in story_ids:
                    story_ids.append(str(prompt.story_id))
                
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
        
        # Set story IDs for context
        session['story_ids'] = story_ids
        
        # Store job info in a way that matches standard jobs
        async_service.processing_jobs[job_id] = {
            "status": "initializing",
            "progress": 0,
            "total": len(prompts_data),
            "completed": 0,
            "results": {},
            "response_ids": [],
            "processing": True,
            "last_activity": time.time(),
            "params": {
                # Match standard job structure but add rerun info
                "model_id": first_prompt.model_id,
                "story_ids": story_ids,
                "question_id": first_prompt.question_id,
                "parameters": {
                    'temperature': first_prompt.temperature,
                    'max_tokens': first_prompt.max_tokens,
                    'top_p': first_prompt.top_p
                },
                # Additional rerun-specific info
                "prompts_data": prompts_data,
                "is_rerun": True
            }
        }
        
        # Store job ID in session
        session['job_id'] = job_id
        
        # Clean up old jobs
        async_service.cleanup_old_jobs()
        
        return redirect(url_for('llm.loading'))
        
    except Exception as e:
        flash(f'Error setting up prompt rerun: {str(e)}', 'danger')
        return redirect(url_for('main.see_all_prompts'))
    
@llm_bp.route('/llm_response', methods=['GET', 'POST'])
def llm_response():
    if request.method == 'POST':
        # The POST handling is already fine - keep it as is
        response_id = request.form.get('response_id')
        if response_id:
            flagged_for_review = f'flagged_for_review_{response_id}' in request.form
            review_notes = request.form.get(f'review_notes_{response_id}', '')
            
            try:
                response = db.session.query(Response).get(response_id)
                if response:
                    response.flagged_for_review = flagged_for_review
                    response.review_notes = review_notes
                    db.session.commit()
                    flash(f'Response {response_id} updated successfully!', 'success')
                else:
                    flash(f'Error: Response {response_id} not found.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating response: {str(e)}', 'danger')

        return redirect(url_for('llm.llm_response'))

    # Get response_ids as before
    response_ids = []
    job_id = session.get('job_id')
    
    if job_id and job_id in async_service.processing_jobs:
        job = async_service.processing_jobs[job_id]
        for result_data in job["results"].values():
            if isinstance(result_data, dict) and "response_id" in result_data:
                response_ids.append(str(result_data["response_id"]))
        
        job["response_ids"] = response_ids
        if response_ids:
            session['response_ids'] = response_ids
    
    if not response_ids:
        response_ids = session.get('response_ids', [])
    
    # Detect if we're dealing with a batch rerun
    is_batch_rerun = False
    
    # Fetch responses with their related data
    response_list = []
    unique_models = set()
    unique_providers = set()
    unique_questions = set()
    
    for response_id in response_ids:
        response = db.session.query(Response).get(response_id)
        if response:
            # Get the prompt associated with this response
            prompt = response.prompt
            story = prompt.story
            question = prompt.question
            model = prompt.model
            
            # Track unique values to determine if we have a batch with different configs
            unique_models.add(model.name)
            unique_providers.add(model.provider.provider_name)
            unique_questions.add(question.content)
            
            # Create a response data object with all needed information
            response_data = {
                'response_id': response.response_id,
                'response_content': response.response_content,
                'flagged_for_review': response.flagged_for_review,
                'review_notes': response.review_notes,
                'story': story,
                'question': question.content,
                'model': model.name,
                'provider': model.provider.provider_name,
                'temperature': prompt.temperature,
                'max_tokens': prompt.max_tokens,
                'top_p': prompt.top_p
            }
            
            response_list.append(response_data)
    
    # Set batch_rerun flag if we have multiple different models, providers, or questions
    is_batch_rerun = (len(unique_models) > 1 or len(unique_providers) > 1 or len(unique_questions) > 1)
    
    # Get common values for the case where we're not in batch mode
    model = session.get('model') if not is_batch_rerun else None
    provider = session.get('provider') if not is_batch_rerun else None
    question_id = session.get('question_id')
    question = db.session.query(Question).get(question_id).content if question_id and not is_batch_rerun else None

    return render_template('llm_response.html', 
                         response_list=response_list,
                         is_batch_rerun=is_batch_rerun,
                         model=model, 
                         provider=provider, 
                         question=question)
