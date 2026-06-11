import pytest
import json
from unittest.mock import patch, MagicMock
from app.configs.queue import RabbitMqAnalysisConsumer
from app.ai.llm_client import LlmTextAnalyticsClient

@patch("app.configs.queue.pika.BlockingConnection")
@patch("app.configs.queue.SessionLocal")
@patch("app.configs.queue.AnalyzeJob")
def test_rabbitmq_consumer_start_and_handling(mock_analyze_job_class, mock_session_local_class, mock_connection_class):
    # Setup mock connections and channels
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_connection_class.return_value = mock_connection

    # Setup mock database session
    mock_session = MagicMock()
    mock_session_local_class.return_value.__enter__.return_value = mock_session

    # Setup mock Use Case instance
    mock_use_case = MagicMock()
    mock_analyze_job_class.return_value = mock_use_case

    # Instantiate consumer
    consumer = RabbitMqAnalysisConsumer()

    # Capture the message handler callback
    callback = None
    def mock_basic_consume(queue, on_message_callback):
        nonlocal callback
        callback = on_message_callback

    mock_channel.basic_consume.side_effect = mock_basic_consume

    # Call start to trigger pika setup
    # We patch start_consuming to avoid infinite blocking loop during tests
    with patch.object(mock_channel, "start_consuming") as mock_start_consuming:
        consumer.start()
        mock_start_consuming.assert_called_once()

    # Verify that the handle callback was registered and test invoking it
    assert callback is not None

    # Simulate receiving a RabbitMQ message payload
    message_payload = {"job_id": "test_job_123", "input_type": "text", "text": "hello"}
    body_bytes = json.dumps(message_payload).encode("utf-8")

    mock_method = MagicMock()
    mock_method.delivery_tag = 999
    mock_method.routing_key = "analysis.jobs.1"

    # Invoke handle callback
    callback(None, mock_method, None, body_bytes)

    # Verify execution of use case and message acknowledgment
    mock_use_case.execute.assert_called_once_with(message_payload)
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=999)


def test_call_llm_json_repairs_malformed_json_once():
    client = LlmTextAnalyticsClient()
    malformed = '{"summary": ["ok"] "sentiment": "neutral"}'
    repaired = '{"summary": ["ok"], "sentiment": "neutral"}'

    with patch.object(client, "_call_llm", side_effect=[malformed, repaired]) as mock_call:
        result = client._call_llm_json("http://llm/v1", "return json")

    assert result == {"summary": ["ok"], "sentiment": "neutral"}
    assert mock_call.call_count == 2
    assert mock_call.call_args_list[0].kwargs["json_mode"] is True
    assert mock_call.call_args_list[1].kwargs["json_mode"] is True


def test_parse_json_object_extracts_object_from_markdown():
    client = LlmTextAnalyticsClient()

    result = client._parse_json_object('```json\n{"agent_score": 80}\n```')

    assert result == {"agent_score": 80}


def test_call_llm_falls_back_from_api_to_local_provider():
    client = LlmTextAnalyticsClient()
    providers = [
        {"name": "LLM_API", "base_url": "http://api/v1", "model": "remote-model", "api_key": "key"},
        {"name": "LLM_LOCAL", "base_url": "http://ollama:11434/v1", "model": "local-model", "api_key": ""},
    ]

    with patch.object(client, "_llm_providers", return_value=providers), patch.object(
        client,
        "_call_llm_provider",
        side_effect=[RuntimeError("timed out after 300s"), '{"ok": true}'],
    ) as mock_provider:
        result = client._call_llm("provider-chain", "prompt", json_mode=True)

    assert result == '{"ok": true}'
    assert mock_provider.call_count == 2
    assert mock_provider.call_args_list[0].args[0]["name"] == "LLM_API"
    assert mock_provider.call_args_list[1].args[0]["name"] == "LLM_LOCAL"
