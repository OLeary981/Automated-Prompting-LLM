import pytest
from app.models.llm import Provider, Model
from sqlalchemy.exc import IntegrityError

@pytest.fixture(autouse=True)
def push_app_context(app):
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()

class TestProviderModel:
    def test_provider_creation(self, session):
        provider = Provider(provider_name="Test Provider")
        session.add(provider)
        session.commit()
        saved = session.query(Provider).filter_by(provider_id=provider.provider_id).first()
        assert saved is not None
        assert saved.provider_name == "Test Provider"

    def test_provider_without_name(self, session):
        provider = Provider(provider_name=None)
        session.add(provider)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_provider_repr(self, session):
        provider = Provider(provider_name="Test Provider")
        session.add(provider)
        session.commit()
        saved = session.query(Provider).filter_by(provider_id=provider.provider_id).first()
        repr_str = repr(saved)
        assert str(saved.provider_id) in repr_str
        assert "Test Provider" in repr_str

class TestModelModel:
    def test_model_creation(self, session, test_data):
        provider_id = test_data["ids"]["providers"][0]
        model = Model(
            name="Test Model",
            provider_id=provider_id,
            endpoint="http://localhost",
            request_delay=1.5,
            parameters='{"param": "value"}'
        )
        session.add(model)
        session.commit()
        saved = session.query(Model).filter_by(model_id=model.model_id).first()
        assert saved is not None
        assert saved.name == "Test Model"
        assert saved.provider_id == provider_id
        assert saved.endpoint == "http://localhost"
        assert saved.request_delay == 1.5
        assert saved.parameters == '{"param": "value"}'

    def test_model_without_name(self, session, test_data):
        provider_id = test_data["ids"]["providers"][0]
        model = Model(
            name=None,
            provider_id=provider_id,
            endpoint="http://localhost",
            request_delay=1.5,
            parameters='{"param": "value"}'
        )
        session.add(model)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_model_without_provider(self, session):
        model = Model(
            name="No Provider Model",
            provider_id=None,
            endpoint="http://localhost",
            request_delay=1.5,
            parameters='{"param": "value"}'
        )
        session.add(model)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_model_repr(self, session, test_data):
        provider_id = test_data["ids"]["providers"][0]
        model = Model(
            name="Test Model",
            provider_id=provider_id,
            endpoint="http://localhost",
            request_delay=1.5,
            parameters='{"param": "value"}'
        )
        session.add(model)
        session.commit()
        saved = session.query(Model).filter_by(model_id=model.model_id).first()
        repr_str = repr(saved)
        assert str(saved.model_id) in repr_str
        assert "Test Model" in repr_str