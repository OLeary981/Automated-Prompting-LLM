import asyncio
import atexit
import logging
import threading
import time
import uuid
from threading import Thread

logger = logging.getLogger(__name__) 

processing_jobs = {}
_event_loop = None
_event_loop_lock = threading.Lock()
_background_thread = None
_initialized = False  # Add this flag to track initialization status
_atexit_registered = False
processing_jobs_lock = threading.Lock()

#consider moving these to config later?
MAX_CONCURRENT_JOBS = 5
COMPLETED_EXPIRY_SEC = 1800
STALLED_EXPIRY_SEC = 7200

def init_async_service(app=None):
    """Initialize the async service - only runs once"""
    global _background_thread, _event_loop, _initialized, _atexit_registered

    #prevents multiple calls to shut down_async_service (issue seen in logs)
    if not _atexit_registered:
        atexit.register(shutdown_async_service)
        _atexit_registered = True

    # Check if already initialized to prevent duplicate initialization
    if _initialized:
        logger.debug("Async service already initialized, skipping.") #less stuff in logs for now.
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
    
    loop = asyncio.new_event_loop() #make a new loop fir this thread (outside the main threads event lopp)
    _background_thread.loop = loop #attaches the loop to the background thread object (in case need to access it later)
    asyncio.set_event_loop(loop) #asynchio code will now run in this loop.
    with _event_loop_lock:
        _event_loop = loop # make the loop global
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
    
    logger.info("In async_service, create_job (line 75) creating job:")
    job_id = str(uuid.uuid4())
    with processing_jobs_lock:
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
    logger.info(f"In async_service, job created: {job_id}")

    return job_id



def can_start_new_job():
    """Check if we can start a new job based on current load"""
    # Count active jobs (those with processing=True and recent activity)
    current_time = time.time()
    active_jobs = 0
    with processing_jobs_lock:
        for job in processing_jobs.values():
            if job.get("processing", False) and current_time - job.get("last_activity", 0) < 60:
                active_jobs += 1
        
    # Limit to 5 concurrent jobs (adjust based on your server capacity)
    return active_jobs < 5

async def process_llm_requests(app, job_id, model_id=None, story_ids=None, question_id=None, parameters=None):
    """Process all LLM requests for the given job"""
    from app.services import llm_service  # Import here to avoid circular imports

    logger.info(f"In async_service process_llm_requests (line116) START for job: {job_id}, check on model id: {model_id}")
    
    try:
        with app.app_context():
            with processing_jobs_lock:
                job = processing_jobs.get(job_id)
                if not job:
                    logger.error(f"Job ID {job_id} not found in processing_jobs")
                    return

                # Initialize job status
                job["status"] = "running"
                job["completed"] = 0
                job["results"] = {}
                job["progress"] = 0
                logger.info(f"Job initialized: {job}")

            try:
                is_rerun = job.get("params", {}).get("is_rerun", False)
                prompts_data = job.get("params", {}).get("prompts_data", [])

                if is_rerun and prompts_data:
                    logger.info("Detected rerun prompts. Processing...")
                    await process_rerun_prompts(app, job_id, prompts_data)
                else:
                    logger.info(f"Processing {len(story_ids)} stories...")
                    await process_stories(app, job_id, model_id, story_ids, question_id, parameters)

                # Extract response IDs
                response_ids = []
                for result_data in job["results"].values():
                    if isinstance(result_data, dict) and "response_id" in result_data:
                        response_ids.append(str(result_data["response_id"]))
                job["response_ids"] = response_ids

                job["status"] = "completed"
                job["progress"] = 100
                logger.info(f"Job {job_id} completed with {len(response_ids)} responses.")

                await asyncio.sleep(300)  # 5 mins to keep job alive

            except Exception as e:
                logger.error(f"Error inside LLM processing block: {str(e)}", exc_info=True)
                job["status"] = "error"
                job["error"] = str(e)

            finally:
                with processing_jobs_lock:
                    if job_id in processing_jobs:
                        job["processing"] = False
                        logger.info(f" Job {job_id} marked as not processing.")

    except Exception as outer_ex:
        logger.exception(f"Unhandled exception in process_llm_requests({job_id}): {outer_ex}")


async def process_rerun_prompts(app, job_id, prompts_data):
    """Process a batch of prompts for rerunning"""

    logger.info(f"In async_service process_rerun_prompts (line 175) START for job: {job_id}")
    from app.services import (
        llm_service,
        question_service,
        story_service,
    )
    # Validate services are available
    if not hasattr(story_service, 'get_story_by_id'):
        raise RuntimeError("story_service.get_story_by_id function not found")
    if not hasattr(question_service, 'get_question_by_id'):
        raise RuntimeError("question_service.get_question_by_id function not found")

    if not prompts_data:
        logger.warning(f"No prompts data provided for job {job_id}")
        return

    with processing_jobs_lock:
        job = processing_jobs[job_id]

    for i, prompt_data in enumerate(prompts_data):
        with processing_jobs_lock:
            # Check if job is still processing
            if job_id not in processing_jobs:
                return

            # Check if prompt data is valid
            if not isinstance(prompt_data, dict):
                logger.error(f"Invalid prompt data format for job {job_id}")
                continue

        # Check if job has been cancelled
        with processing_jobs_lock:
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
                    with processing_jobs_lock:
                        job["results"][prompt_id] = {'error': 'Story or question not found'}
                    continue

            # Delay is outside app context since it's async
            if i > 0 and request_delay > 0:
                await asyncio.sleep(request_delay)

            # Make the actual API call through the service layer
            # response = await run_llm_call_in_executor(
            #     provider_name=provider_name,  # these can be overridden inside call_llm
            #     story=None,
            #     question=None,
            #     story_id=prompt_data["story_id"],
            #     question_id=prompt_data["question_id"],
            #     model_name=model_name,
            #     model_id=model_id,
            #     prompt_id=prompt_id,
            #     **parameters  #suggested alternative is **{} unpacking syntax
            # )

            response = await run_llm_call_in_executor(
                app,
                provider_name,
                story.content,
                question.content,
                prompt_data["story_id"],
                prompt_data["question_id"],
                model_name,
                model_id,
                prompt_id=prompt_id,
                **parameters
            )

            with processing_jobs_lock:
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

                # Calculate and update progress percentage
                progress = int((job["completed"] / job["total"]) * 100)
                job["progress"] = progress
                job["last_activity"] = time.time()

        except Exception as e:
            logger.error(f"Error processing prompt {prompt_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            with processing_jobs_lock:
                job["results"][prompt_id] = {'error': str(e)}

async def process_stories(app, job_id, model_id, story_ids, question_id, parameters):
    """Process each story in the job"""
    from app.services import llm_service, question_service, story_service
    logger.info(f"In async_service process_stories (line 281) START for job: {job_id}")
    if not story_ids:
        logger.warning(f"No story IDs provided for job {job_id}")
        return

    with processing_jobs_lock:
        job = processing_jobs[job_id]
        total_stories = len(story_ids)

    for i, story_id in enumerate(story_ids):
        with processing_jobs_lock: #move inside the loop as otherwise loop locks up
            if job_id not in processing_jobs:
                return
            logger.info(f"Processing story {i+1}/{total_stories} — story_id: {story_id}")

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
                    with processing_jobs_lock:
                        job["results"][story_id] = {'error': 'Story or question not found'}
                    continue

            # Rate limiting delay outside of context manager
            if i > 0 and request_delay > 0:
                await asyncio.sleep(request_delay)

            # Make the actual API call through the service layer
            logger.info(f"Calling LLM for story {story_id}")
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

            with processing_jobs_lock:
                job["completed"] += 1
                if response:
                    logger.info(f"In async_service process_stories (line 328) check on response_id: {response['response_id']}")
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

                # Calculate and update progress percentage
                progress = int((job["completed"] / job["total"]) * 100)
                job["progress"] = progress
                job["last_activity"] = time.time()

        except Exception as e:
            logger.error(f"Error processing story {story_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            with processing_jobs_lock:
                job["results"][story_id] = {'error': str(e)}

async def run_llm_call_in_executor(app, provider_name, story_content, question_content, story_id, question_id, model_name, model_id, **parameters):
    """Run a synchronous LLM call in an executor thread"""
    from app.services import llm_service  # Import here to avoid circular imports
    logger.info(f"In async_service run_llm_call_in_executor (line 353) check on model id: {model_id}")
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
    with processing_jobs_lock:    
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