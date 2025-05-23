# This allows me to share fixtures (test data) across different files/modules (real python https://realpython.com/pytest-python-testing/)

import datetime
import logging
import os
import tempfile

import pytest
from sqlalchemy import event, text

from app import create_app, db
from app.models import (
    Category,
    Field,
    Model,
    Prompt,
    Provider,
    Question,
    Response,
    Run,
    Story,
    StoryCategory,
    Template,
    Word,
)

# Disable verbose test logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


@pytest.fixture(scope='function')
def app():
    db_fd, db_path = tempfile.mkstemp()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}?foreign_keys=ON',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key'
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        @event.listens_for(db.engine, "connect") #have to make sure the constraint is always set (solving problem in test_stories.py)
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        app.config.update({
            "TESTING": True,
            "SERVER_NAME": "localhost.localdomain",  # Needed for url_for() outside request
            "PREFERRED_URL_SCHEME": "http",          # Optional, avoids https:// warnings
        })


        db.create_all()
        result = db.session.execute(text("PRAGMA foreign_keys;")).scalar()
        if result != 1:
            print("WARNING: Foreign key constraints could not be enabled!")
    
        yield app  

    
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not clean up test database file: {e}")


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def session(app):
    """Create a new database session for a test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create a session bound to the connection
        session = db.session
        
        yield session
        
        # Close the session and rollback transaction
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function')
def test_data(session):
    import datetime

    from app.models import (
        Category,
        Field,
        Model,
        Prompt,
        Provider,
        Question,
        Response,
        Story,
        StoryCategory,
        Template,
        Word,
    )

    # Create Providers
    provider1 = Provider(provider_name="Test Provider")
    provider2 = Provider(provider_name="Another Provider")
    session.add_all([provider1, provider2])
    session.commit()

    # Create Models
    model1 = Model(
        name="Test Model",
        provider_id=provider1.provider_id,
        endpoint="placeholder",
        request_delay=5,
        parameters="{}"
    )
    model2 = Model(
        name="GPT-4",
        provider_id=provider2.provider_id,
        endpoint="placeholder",
        request_delay=5,
        parameters="{}"
    )
    session.add_all([model1, model2])
    session.commit()

    # Create Templates
    template1 = Template(content="This is a {animal} template with {action}.")
    template2 = Template(content="The {color} {object} is on the {location}.")
    template3 = Template(content="The {no_words_field} is on the {object}.")
    session.add_all([template1, template2, template3])
    session.commit()

    # Create Categories
    category1 = Category(category="Test Category")
    category2 = Category(category="Another Category")
    session.add_all([category1, category2])
    session.commit()

    # Create Fields and Words
    animal_field = Field(field="animal")
    action_field = Field(field="action")
    color_field = Field(field="color")
    object_field = Field(field="object")
    location_field = Field(field="location")

    cat_word = Word(word="cat")
    dog_word = Word(word="dog")
    run_word = Word(word="run")
    jump_word = Word(word="jump")
    red_word = Word(word="red")
    blue_word = Word(word="blue")
    ball_word = Word(word="ball")
    table_word = Word(word="table")
    floor_word = Word(word="floor")

    animal_field.words.extend([cat_word, dog_word])
    action_field.words.extend([run_word, jump_word])
    color_field.words.extend([red_word, blue_word])
    object_field.words.append(ball_word)
    location_field.words.extend([table_word, floor_word])

    session.add_all([animal_field, action_field, color_field, object_field, location_field])
    session.commit()

    # Create Stories
    story1 = Story(content="This is a cat template with run.", template_id=template1.template_id)
    story2 = Story(content="This is a dog template with jump.", template_id=template1.template_id)
    story3 = Story(content="The red ball is on the table.", template_id=template2.template_id)
    story4 = Story(content="The blue ball is on the floor.", template_id=template2.template_id)
    story5 = Story(content="This is a story5 without a template and with no category associations.")
    story6 = Story(content="This is a story6 without a template and with no category associations.")
    story7 = Story(content="This is a story7 without a template and with no category associations.")
    story8 = Story(content="This is a story8 without a template and with no category associations.")
    story9 = Story(content="This is a story9 without a template and with no category associations.")
    story10 = Story(content="This is a story10 without a template and with no category associations.")
    story11 = Story(content="This is a story11 without a template and with no category associations.")
    story12 = Story(content="This is a story12 without a template and with no category associations.")
    story13 = Story(content="This is a story13 without a template and with no category associations.")
    story14 = Story(content="This is a story14 without a template and with no category associations.")
    story15= Story(content="This is a story15 without a template and with no category associations.")
    story16 = Story(content="This is a story16 without a template and with no category associations.")
    story17 = Story(content="This is a story17 without a template and with no category associations.")
    story18 = Story(content="This is a story18 without a template and with no category associations.")
    story19 = Story(content="This is a story19 without a template and with no category associations.")
    story20 = Story(content="This is a story20 without a template and with no category associations.")
    story21 = Story(content="This is a story21 without a template and with no category associations.")
    session.add_all([story1, story2, story3, story4, story5, story6, story7, story8, story9, story10,
                     story11, story12, story13, story14, story15, story16, story17, story18, story19, story20,
                     story21])
    session.commit()

    # Story-Category relationships
    sc1 = StoryCategory(story_id=story1.story_id, category_id=category1.category_id)
    sc2 = StoryCategory(story_id=story2.story_id, category_id=category2.category_id)
    sc3 = StoryCategory(story_id=story3.story_id, category_id=category1.category_id)
    session.add_all([sc1, sc2, sc3])
    session.commit()

    # Questions
    question1 = Question(content="What is the main theme of this story?")
    question2 = Question(content="What emotions does this story evoke?")
    session.add_all([question1, question2])
    session.commit()

    # Prompts
    prompt1 = Prompt(
        model_id=model1.model_id, story_id=story1.story_id,
        question_id=question1.question_id, temperature=0.7,
        max_tokens=100, top_p=1.0, payload="Test payload content"
    )
    prompt2 = Prompt(
        model_id=model2.model_id, story_id=story2.story_id,
        question_id=question2.question_id, temperature=0.5,
        max_tokens=150, top_p=0.9, payload="Test payload content"
    )
    session.add_all([prompt1, prompt2])
    session.commit()

    # Create Runs for test responses (needed after migration to make run_id non-nulable)
    run1 = Run(description="Test Run 1")
    run2 = Run(description="Test Run 2")
    session.add_all([run1, run2])
    session.commit()

    # Responses
    now = datetime.datetime.utcnow()
    response1 = Response(
        prompt_id=prompt1.prompt_id,
        response_content="conf_test_response_content",
        full_response="...", timestamp=now, flagged_for_review=False,
        run_id=run1.run_id
    )
    response2 = Response(
        prompt_id=prompt2.prompt_id,
        response_content="The story evokes feelings of playfulness and energy.",
        full_response="...", timestamp=now, flagged_for_review=True,
        review_notes="Contains overly simplistic analysis",
        run_id=run2.run_id
    )
    session.add_all([response1, response2])
    session.commit()
    
    #Flask session referred to as "sess" so renamed this 
    sess_data = {
                'story_ids': ['1', '2', '3'],
                'question_id': '42',
                'model': 'Test Model',
                'provider': 'Test Provider',
                'model_id': '123',
                'parameters': {'temperature': '0.7'},
                'stories_source': 'source',
                'template_ids': ['10', '11'],
                
            }
    
    return {
        "sess_data": sess_data,      

        "ids": {
            "providers": [provider1.provider_id, provider2.provider_id],
            "models": [model1.model_id, model2.model_id],
            "templates": [template1.template_id, template2.template_id, template3.template_id],
            "categories": [category1.category_id, category2.category_id],
            "stories": [story1.story_id, story2.story_id, story3.story_id, story4.story_id, story5.story_id, story6.story_id, story7.story_id, story8.story_id, story9.story_id, story10.story_id,
                        story11.story_id, story12.story_id, story13.story_id, story14.story_id, story15.story_id, story16.story_id, story17.story_id, story18.story_id, story19.story_id, story20.story_id, story21.story_id],
            "story_categories": [(sc1.story_id, sc1.category_id), (sc2.story_id, sc2.category_id), (sc3.story_id, sc3.category_id)],
            "questions": [question1.question_id, question2.question_id],
            "prompts": [prompt1.prompt_id, prompt2.prompt_id],
            "responses": [response1.response_id, response2.response_id],
            "fields": {
                "animal": animal_field.field_id,
                "action": action_field.field_id,
                "color": color_field.field_id,
                "object": object_field.field_id,
                "location": location_field.field_id,
            },
            "words": {
                "cat": cat_word.word_id,
                "dog": dog_word.word_id,
                "run": run_word.word_id,
                "jump": jump_word.word_id,
                "red": red_word.word_id,
                "blue": blue_word.word_id,
                "ball": ball_word.word_id,
                "table": table_word.word_id,
                "floor": floor_word.word_id,
            },
            "runs": [run1.run_id, run2.run_id],
        },
        "objects": {
            "template1": template1,  # Use with care: still session-bound
            "stories": [story1, story2, story3, story4, story5, story6, story7, story8, story9, story10,
                        story11, story12, story13, story14, story15, story16, story17, story18, story19, story20, story21], 
            "category1": category1,
            "question1": question1,
            # Add more if needed in specific test functions
        }
    }



@pytest.fixture
def mock_async_service(monkeypatch):
    """Mock the async service to avoid actual background tasks during tests."""
    class MockAsyncService:
        def __init__(self):
            self.processing_jobs = {}
            
        def process_prompt(self, prompt_id, **kwargs):
            """Mock the prompt processing function."""
            self.processing_jobs[prompt_id] = {
                "status": "completed",
                "processing": False,
                "result": {"success": True, "response_id": 999}
            }
            return {"job_id": prompt_id}
            
        def init_async_service(self, app):
            """Mock initialization."""
            pass
            
        def cancel_all_jobs(self):
            """Mock cancel all jobs."""
            job_count = len(self.processing_jobs)
            self.processing_jobs.clear()
            return job_count
        
    mock_service = MockAsyncService()
    monkeypatch.setattr("app.services.async_service", mock_service)
    return mock_service


@pytest.fixture
def auth_client(client):
    """
    A test client with authentication session variables set.
    Use this if your routes require authentication.
    """
    with client.session_transaction() as session:
        session['logged_in'] = True
        session['user_id'] = 1
        session['username'] = 'test_user'
    return client


@pytest.fixture
def with_selected_story(client):
    """A test client with selected story in session."""
    with client.session_transaction() as session:
        session['story_ids'] = ['1', '2']
    return client


@pytest.fixture
def with_selected_question(client):
    """A test client with selected question in session."""
    with client.session_transaction() as session:
        session['question_id'] = '1'
        #session['question_content'] = 'What is the main theme of this story?'
    return client


@pytest.fixture
def with_selected_model(client):
    """A test client with selected model in session."""
    with client.session_transaction() as session:
        session['model_id'] = '1'
        session['model'] = 'Test Model'
        session['provider'] = 'Test Provider'
    return client


@pytest.fixture
def with_parameters(client):
    """A test client with LLM parameters in session."""
    with client.session_transaction() as session:
        session['parameters'] = {
            'temperature': 0.7,
            'max_tokens': 100,
            'top_p': 1.0
        }
    return client

@pytest.fixture
def dummy_job():
    class DummyTask:
        def __init__(self):
            self._done = False
            self._cancelled = False
        def done(self):
            return self._done
        def cancel(self):
            self._cancelled = True

    dummy_task = DummyTask()
    from app.services import async_service
    async_service.processing_jobs['job1'] = {"task": dummy_task, "status": "running", "processing": True}
    yield dummy_task
    async_service.processing_jobs.clear()

@pytest.fixture
def dummy_job_exception():
    class DummyTask:
        def done(self): return False
        def cancel(self): raise RuntimeError("Cancel failed")
    from app.services import async_service
    async_service.processing_jobs['job1'] = {"task": DummyTask(), "status": "running", "processing": True}
    yield
    async_service.processing_jobs.clear()