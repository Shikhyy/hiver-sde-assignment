import pytest
from unittest.mock import patch, MagicMock
from pipeline import HiverPipeline, ClassificationResult

@pytest.fixture
def pipeline():
    # We mock the environment variable so it doesn't fail if the key is missing in CI/CD
    with patch('os.environ.get', return_value='fake_key'):
        with patch('google.genai.Client') as mock_client:
            return HiverPipeline()

def test_pipeline_initialization(pipeline):
    assert pipeline.brand == "AppleSupport"
    assert pipeline.client is not None

def test_classify_and_route(pipeline):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = '{"intent": "technical_issue", "action": "auto", "reason": "Standard battery issue"}'
    
    # We need to mock the client's generate_content call
    pipeline.client.models.generate_content.return_value = mock_response
    
    result = pipeline.classify_and_route("My battery is dying fast")
    
    assert isinstance(result, ClassificationResult)
    assert result.intent == "technical_issue"
    assert result.action == "auto"

def test_draft_reply(pipeline):
    mock_response = MagicMock()
    mock_response.text = "This is a drafted reply."
    pipeline.client.models.generate_content.return_value = mock_response
    
    reply = pipeline.draft_reply("Help me", "technical_issue")
    assert reply == "This is a drafted reply."

def test_process_escalation(pipeline):
    # If it decides to escalate, it shouldn't draft a reply.
    pipeline.classify_and_route = MagicMock(return_value=ClassificationResult(
        intent="complaint", 
        action="escalate", 
        reason="Angry customer"
    ))
    pipeline.draft_reply = MagicMock() # Should not be called
    
    result = pipeline.process("You guys are the worst!")
    
    assert result['action'] == "escalate"
    assert result['draft'] == "[ESCALATED TO HUMAN AGENT]"
    pipeline.draft_reply.assert_not_called()
