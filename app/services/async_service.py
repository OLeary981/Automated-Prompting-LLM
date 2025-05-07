import asyncio
import threading
import time
from threading import Thread
import atexit
import logging
import time
import uuid

logger = logging.getLogger(__name__) 

processing_jobs = {}
_event_loop = None
_event_loop_lock = threading.Lock()
_background_thread = None
_initialized = False  # Add this flag to track initialization status

def init_async_service(app=None):
    """Initialize the async service - only runs once"""
    global _background_thread, _event_loop, _initialized

    # Check if already initialized to prevent duplicate initialization
    if _initialized:
        logger.info("Async service already initialized, skipping.")
        return

    # Mark as initialized BEFORE creating the thread
    _initialized = True
    
    logger.info(f"Initializing async service for app: {app.name if app else 'None'}")
    _background_thread = Thread(target=run_async_loop, daemon=True)
    _background_thread.start()
    time.sleep(0.1)  # Brief delay to let the thread start
    logger.info("Async service initialized with background event loop")

def run_async_loop():
    """Run the asyncio event loop in a background thread"""
    global _event_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with _event_loop_lock:
        _event_loop = loop
    
    try:
        loop.run_forever()
    except Exception as e:
        logger.error(f"Error in async event loop: {str(e)}")
    finally:
        logger.warning("Event loop exited - this should not happen during normal operation!")

def get_event_loop():
    """Get the running event loop (from any thread)"""
    global _event_loop
    with _event_loop_lock:
        if _event_loop is None:
            raise RuntimeError("Event loop not initialized")
        return _event_loop


def create_job(model_id, story_ids, question_id, parameters):
    """Create a new processing job and return its ID"""
    job_id = str(uuid.uuid4())
    
    processing_jobs[job_id] = {
        "status": "initializing",
        "progress": 0,
        "total": len(story_ids),
        "completed": 0,
        "results": {},
        "processing": True,
        "last_activity": time.time(),
        "params": {
            "model_id": model_id,
            "story_ids": story_ids,
            "question_id": question_id,
            "parameters": parameters
        }
    }
    
    return job_id



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

async def process_llm_requests(app, job_id, model_id=None, story_ids=None, question_id=None, parameters=None):
    """Process all LLM requests for the given job"""
    from app.services import llm_service  # Import here to avoid circular imports
    logger.info(f"Starting process_llm_requests for job: {job_id}")
    with app.app_context():
        job = processing_jobs[job_id]
        
        # Initialize job status
        job["status"] = "running"
        job["completed"] = 0
        job["results"] = {}
        job["progress"] = 0
        logger.info(f"Job initialized: {job}")
        try:
            # Check if this is a rerun job
            is_rerun = job.get("params", {}).get("is_rerun", False)
            prompts_data = job.get("params", {}).get("prompts_data", [])
            
            if is_rerun and prompts_data:
                # Process each prompt for rerun
                await process_rerun_prompts(app, job_id, prompts_data)
            else:
                # Original story-by-story processing
                await process_stories(app, job_id, model_id, story_ids, question_id, parameters)
            
            # Extract all response IDs from results and store in a consistent place
            response_ids = []
            for result_data in job["results"].values():
                if isinstance(result_data, dict) and "response_id" in result_data:
                    response_ids.append(str(result_data["response_id"]))

            # Store response IDs in the job in a standard way
            job["response_ids"] = response_ids

            # Mark job as completed
            job["status"] = "completed"
            job["progress"] = 100
            
            # Keep the results in memory for a few minutes
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
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

async def process_rerun_prompts(app, job_id, prompts_data):
    """Process a batch of prompts for rerunning"""
    from app.services import llm_service, question_service, story_service  # Import here to avoid circular imports
        # Validate services are available
    if not hasattr(story_service, 'get_story_by_id'):
        raise RuntimeError("story_service.get_story_by_id function not found")
    if not hasattr(question_service, 'get_question_by_id'):
        raise RuntimeError("question_service.get_question_by_id function not found")
    
    if not prompts_data:
        logger.warning(f"No prompts data provided for job {job_id}")
        return
    


    job = processing_jobs[job_id]
    
    for i, prompt_data in enumerate(prompts_data):
        # Check if job has been cancelled
        if job_id not in processing_jobs:
            return
        
        # Get the prompt data
        prompt_id = prompt_data.get('prompt_id')
        if not prompt_id:
            logger.error(f"Missing prompt_id in prompt data for job {job_id}")
            continue
        model_id = prompt_data['model_id']
        story_id = prompt_data['story_id']
        question_id = prompt_data['question_id']
        parameters = prompt_data['parameters']
        
        try:
            # Get the story, question, and model details
            with app.app_context():
                story = story_service.get_story_by_id(story_id)
                question = question_service.get_question_by_id(question_id)
                provider_name = llm_service.get_provider_name_by_model_id(model_id)
                model_name = llm_service.get_model_name_by_id(model_id)
                request_delay = llm_service.get_request_delay_by_model_id(model_id)
                if not story or not question:
                        logger.error(f"Story or question not found for prompt {prompt_id}")
                        job["results"][prompt_id] = {'error': 'Story or question not found'}
                        continue
            
            # Delay is outside app context since it's async
            if i > 0 and request_delay > 0:
                await asyncio.sleep(request_delay)
            
            # Make the actual API call through the service layer
            response = await run_llm_call_in_executor(
                app,
                provider_name,
                story.content,
                question.content,
                story_id,
                question_id,
                model_name,
                model_id,
                prompt_id=prompt_id,
                **parameters
            )
            
            # Update job state
            job["completed"] += 1
            if response:
                if isinstance(response, dict) and "response_id" in response:
                    job["results"][prompt_id] = {'response_id': response["response_id"]}
                elif hasattr(response, 'response_id'):
                    job["results"][prompt_id] = {'response_id': response.response_id}
                else:
                    logger.warning(f"Unexpected response format: {type(response)}")
                    job["results"][prompt_id] = {'error': 'Invalid response format'}
            else:
                logger.warning(f"Empty response received for prompt {prompt_id}")
                job["results"][prompt_id] = {'error': 'Empty response'}
                
        except Exception as e:
            logger.error(f"Error processing prompt {prompt_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            job["results"][prompt_id] = {'error': str(e)}
        
        # Calculate and update progress percentage
        progress = int((job["completed"] / job["total"]) * 100)
        job["progress"] = progress
        job["last_activity"] = time.time()

async def process_stories(app, job_id, model_id, story_ids, question_id, parameters):
    """Process each story in the job"""
    from app.services import llm_service, story_service, question_service
    
    if not story_ids:
        logger.warning(f"No story IDs provided for job {job_id}")
        return
        
    job = processing_jobs[job_id]
    
    for i, story_id in enumerate(story_ids):
        if job_id not in processing_jobs:
            return
            
        try:
            # Get all needed data within app context
            with app.app_context():
                story = story_service.get_story_by_id(story_id)
                question = question_service.get_question_by_id(question_id)
                provider_name = llm_service.get_provider_name_by_model_id(model_id)
                model_name = llm_service.get_model_name_by_id(model_id)
                request_delay = llm_service.get_request_delay_by_model_id(model_id)
                
                if not story or not question:
                    logger.error(f"Story or question not found for story_id {story_id}")
                    job["results"][story_id] = {'error': 'Story or question not found'}
                    continue
            
            # Rate limiting delay outside of context manager
            if i > 0 and request_delay > 0:
                await asyncio.sleep(request_delay)
            
            # Make the actual API call through the service layer
            response = await run_llm_call_in_executor(
                app,
                provider_name,
                story.content,
                question.content,
                story_id,
                question_id,
                model_name,
                model_id,
                **parameters
            )
            
            # Update job state
            job["completed"] += 1
            if response:
                if isinstance(response, dict) and "response_id" in response:
                    job["results"][story_id] = {'response_id': response["response_id"]}
                elif hasattr(response, 'response_id'):
                    job["results"][story_id] = {'response_id': response.response_id}
                else:
                    logger.warning(f"Unexpected response format: {type(response)}")
                    job["results"][story_id] = {'error': 'Invalid response format'}
            else:
                logger.warning(f"Empty response received for story {story_id}")
                job["results"][story_id] = {'error': 'Empty response'}
                
        except Exception as e:
            logger.error(f"Error processing story {story_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            job["results"][story_id] = {'error': str(e)}
        
        # Calculate and update progress percentage
        progress = int((job["completed"] / job["total"]) * 100)
        job["progress"] = progress
        job["last_activity"] = time.time()

async def run_llm_call_in_executor(app, provider_name, story_content, question_content, story_id, question_id, model_name, model_id, **parameters):
    """Run a synchronous LLM call in an executor thread"""
    from app.services import llm_service  # Import here to avoid circular imports
    
    def call_llm_with_context():
        with app.app_context():
            return llm_service.call_llm(
                provider_name, 
                story_content, 
                question_content, 
                story_id, 
                question_id, 
                model_name, 
                model_id,
                **parameters
            )
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, call_llm_with_context)


def cleanup_old_jobs():
    """Clean up old and completed jobs from the processing_jobs dictionary"""
    global processing_jobs
    current_time = time.time()
    jobs_to_remove = []
    
    for job_id, job in processing_jobs.items():
        # Remove completed/error jobs after 30 minutes
        if job.get("status") in ["completed", "error", "cancelled"]:
            if current_time - job.get("last_activity", 0) > 1800:  # 30 minutes
                jobs_to_remove.append(job_id)
        # Remove stalled jobs after 2 hours
        elif current_time - job.get("last_activity", 0) > 7200:  # 2 hours
            jobs_to_remove.append(job_id)
    
    # Remove the jobs
    for job_id in jobs_to_remove:
        if job_id in processing_jobs:
            logger.info(f"Cleaning up old job: {job_id}")
            del processing_jobs[job_id]

def shutdown_async_service():
    global _event_loop
    with _event_loop_lock:
        if _event_loop is not None and not _event_loop.is_closed():
            _event_loop.call_soon_threadsafe(_event_loop.stop)
            logger.info("Async event loop stopped")

# Register shutdown function to clean up resources
atexit.register(shutdown_async_service)