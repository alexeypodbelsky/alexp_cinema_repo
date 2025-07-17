import uuid
from datetime import datetime
import json
import os
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

app = FastAPI()

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
MOVIE_TOPIC = "movie-events"
USER_TOPIC = "user-events"
PAYMENT_TOPIC = "payment-events"

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKERS],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    api_version=(0, 10, 1),
)

consumer = KafkaConsumer(
    MOVIE_TOPIC,
    USER_TOPIC,
    PAYMENT_TOPIC,
    bootstrap_servers=[KAFKA_BROKERS],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="events-group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    api_version=(0, 10, 1),
)


class MovieEvent(BaseModel):
    movie_id: int
    title: str
    action: str
    user_id: Optional[int] = None
    rating: Optional[float] = None
    genres: Optional[list[str]] = None
    description: Optional[str] = None


class UserEvent(BaseModel):
    user_id: int
    action: str
    username: Optional[str] = None
    email: Optional[str] = None
    timestamp: str


class PaymentEvent(BaseModel):
    payment_id: int
    user_id: int
    amount: float
    status: str
    timestamp: str
    method_type: Optional[str] = None


class EventResponse(BaseModel):
    status: str
    partition: int
    offset: int
    event: dict


async def publish_event(topic: str, event_data: dict) -> EventResponse:
    try:
        loop = asyncio.get_event_loop()
        future = await loop.run_in_executor(
            None,
            producer.send,
            topic,
            event_data,
        )
        record_metadata = future.get(timeout=10)

        event_response = EventResponse(
            status="success",
            partition=record_metadata.partition,
            offset=record_metadata.offset,
            event=event_data,
        )
        return event_response
    except KafkaError as e:
        raise HTTPException(status_code=500, detail=f"Kafka error: {e}")


@app.get("/api/events/health")
async def health_check():
    return {"status": True}


@app.post("/api/events/movie", response_model=EventResponse, status_code=201)
async def create_movie_event(event: MovieEvent):
    event_data = event.dict()
    return await publish_event(MOVIE_TOPIC, event_data)


@app.post("/api/events/user", response_model=EventResponse, status_code=201)
async def create_user_event(event: UserEvent):
    now = datetime.utcnow()

    # Format ISO 8601 string ("2023-10-27T10:00:00Z")
    timestamp_str = now.isoformat() + "Z"  # + "Z" для обозначения UTC

    event_data = event.dict()
    event_data["timestamp"] = timestamp_str
    return await publish_event(USER_TOPIC, event_data)


@app.post("/api/events/payment", response_model=EventResponse, status_code=201)
async def create_payment_event(event: PaymentEvent):
    event_data = event.dict()
    return await publish_event(PAYMENT_TOPIC, event_data)


async def consume_messages():
    print("Consumer started.  Listening for messages...")
    try:
        for message in consumer:
            print("Received message:", message.topic, message.value)
    except Exception as e:
        print(f"Error during consumption: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
