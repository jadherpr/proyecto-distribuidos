import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import config
from .clock import LamportClock
from .db import Database, utc_now
from .federation import Federation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("server")

db: Database
clock: LamportClock
federation: Federation


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, clock, federation
    db = Database(config.DB_PATH)
    clock = LamportClock()
    clock.restore(db.max_lamport())
    federation = Federation(db, clock)
    logger.info(
        "START server=%s url=%s central=%s clock=%d db=%s",
        config.GROUP_NAME,
        config.PUBLIC_URL,
        config.CENTRAL_URL,
        clock.value,
        config.DB_PATH,
    )
    task = asyncio.create_task(federation.run())
    yield
    task.cancel()


app = FastAPI(title=f"Chat {config.GROUP_NAME}", lifespan=lifespan)


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class MessageCreate(BaseModel):
    from_user: str = Field(alias="from")
    body: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class FedMessage(BaseModel):
    model_config = {"extra": "ignore", "populate_by_name": True}

    id: str
    from_user: str = Field(alias="from")
    origin: str
    lamport: int
    sent_at: str = ""
    body: str


@app.post("/users")
def create_user(payload: UserCreate):
    local_name = f"{payload.name}@{config.GROUP_NAME}"
    created = db.create_user(local_name)
    if not created:
        raise HTTPException(status_code=409, detail="user already exists")
    logger.info("USER created user=%s", local_name)
    return {"user": local_name}


@app.get("/users")
def list_users():
    return {"users": db.list_users()}


@app.post("/messages")
def send_message(payload: MessageCreate):
    sender = payload.from_user
    if not sender.endswith(f"@{config.GROUP_NAME}"):
        raise HTTPException(status_code=403, detail=f"only local users @ {config.GROUP_NAME} can send")
    if sender not in db.list_users():
        raise HTTPException(status_code=404, detail="unknown user")

    lamport = clock.tick()
    message = {
        "id": str(uuid.uuid4()),
        "from": sender,
        "origin": config.GROUP_NAME,
        "lamport": lamport,
        "sent_at": utc_now(),
        "body": payload.body,
    }
    db.insert_message(
        message["id"], sender, config.GROUP_NAME, lamport, message["sent_at"], payload.body
    )
    db.enqueue_pending(message["id"], message)
    federation.notify_outbound()
    logger.info("LOCAL id=%s from=%s lamport=%d", message["id"], sender, lamport)
    return message


@app.get("/messages")
def get_messages():
    return {"messages": db.list_messages(), "server": config.GROUP_NAME}


@app.get("/status")
def status():
    return {
        "server": config.GROUP_NAME,
        "lamport": clock.value,
        "central_up": federation.central_up,
        "pending": db.pending_count(),
        "users": len(db.list_users()),
        "messages": len(db.list_messages()),
    }


@app.get("/fed/health")
def fed_health():
    return {"server": config.GROUP_NAME, "lamport": clock.value}


@app.post("/fed/messages")
def fed_messages(payload: FedMessage):
    accepted = federation._ingest(payload.model_dump(by_alias=True), source="federation")
    return {"status": "accepted" if accepted else "duplicate"}
