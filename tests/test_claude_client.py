import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from claude_client import ClaudeClient, ClaudeResponse


@pytest.fixture
def client():
    return ClaudeClient(api_key="test-key", skill_id="skill_123")


def test_extract_text_from_response(client):
    """Test extracting text blocks from a Claude API response (no code execution)."""
    response = MagicMock()
    response.content = [
        MagicMock(type="text", text="Here is your document"),
        MagicMock(type="text", text=" - total RD$ 12,435"),
    ]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_123")

    result = client.extract_response(response)
    assert result.text == "Here is your document - total RD$ 12,435"
    assert result.file_ids == []
    assert result.container_id == "container_123"


def test_extract_file_ids_from_response(client):
    """Test extracting file_ids from code execution results."""
    file_block = MagicMock()
    file_block.file_id = "file_abc"
    file_block.type = "file"

    exec_result = MagicMock()
    exec_result.type = "bash_code_execution_result"
    exec_result.content = [file_block]

    tool_result = MagicMock()
    tool_result.type = "bash_code_execution_tool_result"
    tool_result.content = exec_result

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "PDF generated"

    response = MagicMock()
    response.content = [tool_result, text_block]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_456")

    result = client.extract_response(response)
    assert result.text == "PDF generated"
    assert result.file_ids == ["file_abc"]


def test_extract_response_filters_text_before_code_execution(client):
    """Text before code execution blocks should be filtered out (verbose narration)."""
    file_block = MagicMock()
    file_block.file_id = "file_abc"
    file_block.type = "file"

    exec_result = MagicMock()
    exec_result.type = "bash_code_execution_result"
    exec_result.content = [file_block]

    tool_result = MagicMock()
    tool_result.type = "bash_code_execution_tool_result"
    tool_result.content = exec_result

    response = MagicMock()
    response.content = [
        MagicMock(type="text", text="Voy a generar el documento con los siguientes datos..."),
        MagicMock(type="text", text="Calculando totales e ITBIS..."),
        tool_result,
        MagicMock(type="text", text="Aquí está tu cotización."),
    ]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_789")

    result = client.extract_response(response)
    assert result.text == "Aquí está tu cotización."
    assert result.file_ids == ["file_abc"]


def test_extract_response_keeps_all_text_when_no_code_execution(client):
    """When no code execution happens, all text blocks are kept."""
    response = MagicMock()
    response.content = [
        MagicMock(type="text", text="Necesito saber "),
        MagicMock(type="text", text="si incluye ITBIS."),
    ]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_abc")

    result = client.extract_response(response)
    assert result.text == "Necesito saber si incluye ITBIS."
    assert result.file_ids == []


def test_needs_continuation(client):
    response = MagicMock()
    response.stop_reason = "pause_turn"
    assert client.needs_continuation(response) is True

    response.stop_reason = "end_turn"
    assert client.needs_continuation(response) is False
