import pytest
import json
from unittest.mock import patch, MagicMock
from app.infrastructure.queue.rabbitmq_consumer import RabbitMqAnalysisConsumer

@patch("app.infrastructure.queue.rabbitmq_consumer.pika.BlockingConnection")
@patch("app.infrastructure.queue.rabbitmq_consumer.SessionLocal")
@patch("app.infrastructure.queue.rabbitmq_consumer.AnalyzeJob")
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
