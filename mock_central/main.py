import asyncio
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("central")

REGISTRY: dict[str, str] = {}
MESSAGES: list[dict] = []
MESSAGES_LOCK = threading.Lock()
FORWARDED_IDS: set[str] = set()
CLIENT = httpx.AsyncClient(timeout=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await CLIENT.aclose()


app = FastAPI(title="Servidor central simulado", lifespan=lifespan)


class RegisterRequest(BaseModel):
    server: str
    url: str


class IncomingMessage(BaseModel):
    model_config = {"extra": "ignore", "populate_by_name": True}

    id: str
    from_user: str = Field(alias="from")
    origin: str
    lamport: int
    sent_at: str = ""
    body: str


@app.post("/register")
def register(payload: RegisterRequest):
    REGISTRY[payload.server] = payload.url
    logger.info("REGISTER server=%s url=%s total=%d", payload.server, payload.url, len(REGISTRY))
    return {"status": "registered", "servers": sorted(REGISTRY)}


@app.post("/messages")
async def receive_message(payload: IncomingMessage):
    message = payload.model_dump(by_alias=True)
    with MESSAGES_LOCK:
        known = any(m["id"] == message["id"] for m in MESSAGES)
        if not known:
            MESSAGES.append(message)
            targets = {name: url for name, url in REGISTRY.items() if name != message["origin"]}
    if known:
        logger.info("DUP id=%s from=%s", message["id"], message["from"])
        return {"status": "duplicate"}
    logger.info("STORED id=%s from=%s lamport=%d", message["id"], message["from"], message["lamport"])
    for name, url in targets.items():
        asyncio.create_task(forward(name, url, message))
    return {"status": "accepted"}


async def forward(name: str, url: str, message: dict) -> None:
    for attempt in range(1, 4):
        try:
            response = await CLIENT.post(f"{url}/fed/messages", json=message)
            if response.status_code < 400:
                logger.info("FORWARDED id=%s to=%s attempt=%d", message["id"], name, attempt)
                return
            logger.warning("FORWARD rejected id=%s to=%s status=%d", message["id"], name, response.status_code)
        except httpx.HTTPError as error:
            logger.warning("FORWARD failed id=%s to=%s attempt=%d error=%s", message["id"], name, attempt, error)
        await asyncio.sleep(1.0 * attempt)
    logger.error("FORWARD gave up id=%s to=%s", message["id"], name)


@app.get("/history")
def history(since: int = 0):
    with MESSAGES_LOCK:
        messages = sorted(
            (m for m in MESSAGES if m["lamport"] > since),
            key=lambda m: (m["lamport"], m["origin"]),
        )
        return list(messages)


@app.get("/health")
def health():
    return {"status": "ok", "servers": sorted(REGISTRY), "messages": len(MESSAGES)}
