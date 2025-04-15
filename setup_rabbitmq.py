import asyncio
import aio_pika
from config import EXCHANGES, RABBITMQ_CONFIG  # Ensure these are imported from your config

async def setup_exchanges():
    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        login=RABBITMQ_CONFIG["user"],
        password=RABBITMQ_CONFIG["password"]
    )
    channel = await connection.channel()

    # Declare all required exchanges
    for exchange_name in EXCHANGES.values():
        await channel.declare_exchange(exchange_name, type=aio_pika.ExchangeType.TOPIC, durable=True)
        print(f"✅ Declared exchange: {exchange_name}")

    await connection.close()

if __name__ == "__main__":
    asyncio.run(setup_exchanges())
    print("✅ All exchanges set up successfully.")