import asyncio
import aio_pika
import json
import logging
import httpx
from datetime import datetime, timedelta
from config import ROOM_IDS, EXCHANGES, RABBITMQ_CONFIG, SUPABASE_HTTP_CONFIG

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupabaseUpdater")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_HTTP_CONFIG["key"],
    "Authorization": f"Bearer {SUPABASE_HTTP_CONFIG['key']}",
    "Content-Type": "application/json",
}

ROOM_TIMERS = {}  # { room_id: { last_update, last_values, started } }

ALL_DATAPOINTS = [
    "temperature",
    "humidity",
    "co2",
    "power_kw_power_meter",
    "sensitivity",
    "online_status",
    "occupancy",
    "presence_state"
]


async def upsert_room_state_http(room_id, is_occupied, datapoint, health_status="healthy"):
    now = datetime.now().isoformat()
    payload = {
        "room_id": room_id,
        "is_occupied": is_occupied,
        "vacancy_last_updated": now,
        "datapoint": datapoint,
        "health_status": health_status,
        "datapoint_last_updated": now
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SUPABASE_HTTP_CONFIG['url']}/rest/v1/room_states",
                headers=SUPABASE_HEADERS,
                json=payload,
                params={"on_conflict": "room_id,datapoint"}
            )
            if resp.status_code >= 300:
                logger.error(f"❌ Failed to upsert room state to Supabase: {resp.json()}")
            else:
                logger.info(f"🟢 Upserted room state to Supabase: {room_id} - {datapoint}")
    except Exception as e:
        logger.error(f"❌ Supabase request failed: {e}")


async def periodic_room_health_updater(room_id):
    while True:
        await asyncio.sleep(60)
        if room_id in ROOM_TIMERS:
            values = ROOM_TIMERS[room_id]["last_values"]
            for dp in ALL_DATAPOINTS:
                await upsert_room_state_http(room_id, is_occupied=True, datapoint=dp, health_status="healthy")


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process(ignore_processed=True):
        try:
            routing_key = message.routing_key
            raw_body = message.body.decode()
            parsed = json.loads(raw_body)
            room_id = parsed.get("room_id")
            is_occupied = parsed.get("is_occupied", True)
            datapoint = parsed.get("datapoint", "unknown")
            health_status = parsed.get("health_status", "healthy")

            logger.info(f"[SupabaseUpdater] Received {datapoint} for {room_id} | status={health_status}")

            # Save last values for periodic refresh
            if room_id not in ROOM_TIMERS:
                ROOM_TIMERS[room_id] = {
                    "last_values": {},
                    "started": False
                }

            ROOM_TIMERS[room_id]["last_values"][datapoint] = health_status

            if not ROOM_TIMERS[room_id]["started"]:
                asyncio.create_task(periodic_room_health_updater(room_id))
                ROOM_TIMERS[room_id]["started"] = True

            # Immediate upsert
            await upsert_room_state_http(room_id, is_occupied, datapoint, health_status)

        except Exception as e:
            logger.error(f"[SupabaseUpdater] ❌ Error processing message: {e}")


async def main():
    logger.info("[SupabaseUpdater] Connecting to RabbitMQ...")

    connection = await aio_pika.connect_robust(
        host=RABBITMQ_CONFIG["host"],
        port=RABBITMQ_CONFIG["port"],
        login=RABBITMQ_CONFIG["user"],
        password=RABBITMQ_CONFIG["password"],
        virtualhost=RABBITMQ_CONFIG["vhost"]
    )

    async with connection:
        channel = await connection.channel()
        logger.info("[SupabaseUpdater] ✅ Connected to RabbitMQ.")

        fault_exchange = await channel.declare_exchange(
            EXCHANGES["fault_alerts"], aio_pika.ExchangeType.TOPIC, durable=True
        )
        occupancy_exchange = await channel.declare_exchange(
            EXCHANGES["occupancy"], aio_pika.ExchangeType.TOPIC, durable=True
        )

        for room_id in ROOM_IDS:
            for exchange, topic in [(fault_exchange, "fault"), (occupancy_exchange, "occupancy")]:
                routing_key = f"{room_id}.{topic}"
                queue_name = f"{room_id}_{topic}_updater_queue"

                queue = await channel.declare_queue(queue_name, durable=True)
                await queue.bind(exchange, routing_key=routing_key)
                await queue.consume(handle_message)

        logger.info("[SupabaseUpdater] 🟢 Waiting for messages...")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[SupabaseUpdater] 🔴 Stopped by user.")