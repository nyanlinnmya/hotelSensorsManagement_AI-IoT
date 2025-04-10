import pika
import json
import logging
from typing import Callable, Optional
from config import RABBITMQ_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self):
        """Initialize connection and channel with retry logic."""
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """Establish RabbitMQ connection with error handling."""
        try:
            credentials = pika.PlainCredentials(
                RABBITMQ_CONFIG["user"], RABBITMQ_CONFIG["password"]
            )
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_CONFIG["host"],
                    port=RABBITMQ_CONFIG["port"],
                    virtual_host=RABBITMQ_CONFIG["vhost"],
                    credentials=credentials,
                    heartbeat=600,
                )
            )
            
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    def publish(
        self, exchange: str, routing_key: str, message: dict, exchange_type: str = "topic"
    ):
        """Publish a message to a topic exchange."""
        try:
            # Declare exchange (idempotent)
            self.channel.exchange_declare(
                exchange=exchange, exchange_type=exchange_type, durable=True
            )
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),  # Persistent message
            )
            logger.debug(f"Published to {exchange}.{routing_key}: {message}")
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            self.reconnect()

    def subscribe(
        self,
        exchange: str,
        queue_name: str,
        routing_key: str,
        callback: Callable,
        exchange_type: str = "topic",
    ):
        """Subscribe to a queue with a callback."""
        try:
            self.channel.exchange_declare(exchange=exchange, exchange_type=exchange_type)
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.queue_bind(
                queue=queue_name, exchange=exchange, routing_key=routing_key
            )
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False,  # Manual acknowledgments
            )
            logger.info(f"Subscribed to {exchange}.{routing_key}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            self.reconnect()

    def reconnect(self):
        """Attempt to reconnect on failure."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        self.connect()

    def close(self):
        """Cleanup connections."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")

# Test the connection and queue creation
# This part is for testing the connection and queue creation
if __name__ == "__main__":
    print(f"Trying to connect with: {RABBITMQ_CONFIG['user']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}")

    try:
        connection=RabbitMQManager()
        print("✅ Connection successful!")
        channel = connection.connection.channel()
        channel.queue_declare(queue='test_queue')
        print("✅ Queue created successfully!")
        connection.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
    
    # Create manager instance
    manager = RabbitMQManager()
    
    # Test data
    test_exchange = "test_exchange"
    test_queue = "test_queue"
    test_routing_key = "test.key"
    test_message = {
        "id": 123,
        "message": "Hello RabbitMQ!",
        "timestamp": "2023-11-15T12:00:00Z"
    }

    def test_callback(ch, method, properties, body):
        """Example callback for testing subscriptions"""
        try:
            message = json.loads(body)
            logger.info(f"Received message: {message}")
            # Process the message here...
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError:
            logger.error("Failed to decode message")
            ch.basic_nack(delivery_tag=method.delivery_tag)

    try:
        # Test publishing
        logger.info("Testing publish...")
        manager.publish(
            exchange=test_exchange,
            routing_key=test_routing_key,
            message=test_message
        )
        
        # Test subscribing (this will block)
        logger.info("Testing subscribe (Ctrl+C to stop)...")
        manager.subscribe(
            exchange=test_exchange,
            queue_name=test_queue,
            routing_key=test_routing_key,
            callback=test_callback
        )
        
    except KeyboardInterrupt:
        logger.info("Stopping test...")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        manager.close()
        logger.info("Test completed")
