import asyncio
import logging

import httpx

from . import config
from .clock import LamportClock
from .db import Database

logger = logging.getLogger("federation")


class Federation:
    def __init__(self, db: Database, clock: LamportClock) -> None:
        self.db = db
        self.clock = clock
        self.central_up = False
        self._heartbeat_fails = 0
        self._wakeup = asyncio.Event()
        self._client = httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT)

    def notify_outbound(self) -> None:
        self._wakeup.set()

    async def run(self) -> None:
        await asyncio.gather(
            self._register_loop(),
            self._heartbeat_loop(),
            self._sender_loop(),
        )

    async def _register_loop(self) -> None:
        payload = {"server": config.GROUP_NAME, "url": config.PUBLIC_URL}
        while True:
            try:
                response = await self._client.post(f"{config.CENTRAL_URL}/register", json=payload)
                if response.status_code < 400:
                    logger.info("REGISTER ok server=%s url=%s", config.GROUP_NAME, config.PUBLIC_URL)
                else:
                    logger.warning("REGISTER rejected status=%s", response.status_code)
            except httpx.HTTPError as error:
                logger.warning("REGISTER failed error=%s", error)
            await asyncio.sleep(config.REGISTER_INTERVAL)

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                response = await self._client.get(f"{config.CENTRAL_URL}/health")
                alive = response.status_code < 500
            except httpx.HTTPError:
                alive = False

            if alive:
                self._heartbeat_fails = 0
                if not self.central_up:
                    self.central_up = True
                    logger.info("CENTRAL_UP")
                    await self._recover_history()
                    self.notify_outbound()
            else:
                self._heartbeat_fails += 1
                if self.central_up and self._heartbeat_fails >= config.HEARTBEAT_MAX_FAILS:
                    self.central_up = False
                    logger.warning(
                        "CENTRAL_DOWN fails=%d pending=%d",
                        self._heartbeat_fails,
                        self.db.pending_count(),
                    )

            await asyncio.sleep(config.HEARTBEAT_INTERVAL)

    async def _recover_history(self) -> None:
        since = self.db.max_lamport()
        try:
            response = await self._client.get(
                f"{config.CENTRAL_URL}/history", params={"since": since}
            )
        except httpx.HTTPError as error:
            logger.warning("HISTORY failed since=%d error=%s", since, error)
            return

        if response.status_code >= 400:
            logger.warning("HISTORY rejected since=%d status=%s", since, response.status_code)
            return

        messages = response.json()
        if not isinstance(messages, list):
            logger.warning("HISTORY unexpected payload since=%d", since)
            return

        recovered = 0
        for message in sorted(messages, key=lambda m: (m.get("lamport", 0), m.get("origin", ""))):
            if self._ingest(message, source="history"):
                recovered += 1
        logger.info("HISTORY since=%d recovered=%d total=%d", since, recovered, len(messages))

    def _ingest(self, message: dict, source: str) -> bool:
        try:
            message_id = str(message["id"])
            from_user = str(message["from"])
            origin = str(message["origin"])
            lamport = int(message["lamport"])
            body = str(message["body"])
            sent_at = str(message.get("sent_at", ""))
        except (KeyError, TypeError, ValueError):
            logger.warning("RECV invalid source=%s payload=%s", source, message)
            return False

        if self.db.has_message(message_id):
            logger.info("DUP discard id=%s lamport=%d source=%s", message_id, lamport, source)
            return False

        self.db.insert_message(message_id, from_user, origin, lamport, sent_at, body)
        self.clock.observe(lamport)
        logger.info(
            "RECV id=%s from=%s lamport=%d clock=%d source=%s",
            message_id,
            from_user,
            lamport,
            self.clock.value,
            source,
        )
        return True

    async def _sender_loop(self) -> None:
        while True:
            if not self.central_up:
                self._wakeup.clear()
                await self._wakeup.wait()
                continue

            item = self.db.next_pending()
            if item is None:
                self._wakeup.clear()
                await self._wakeup.wait()
                continue

            payload = item["payload"]
            message_id = item["id"]
            attempts = item["attempts"] + 1
            try:
                response = await self._client.post(f"{config.CENTRAL_URL}/messages", json=payload)
            except httpx.HTTPError as error:
                delay = self._backoff(attempts)
                logger.warning(
                    "RETRY id=%s attempt=%d delay=%.2fs error=%s",
                    message_id,
                    attempts,
                    delay,
                    error,
                )
                self.db.mark_pending_attempt(message_id, attempts, self._now() + delay)
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 500:
                delay = self._backoff(attempts)
                logger.warning(
                    "RETRY id=%s attempt=%d delay=%.2fs status=%d",
                    message_id,
                    attempts,
                    delay,
                    response.status_code,
                )
                self.db.mark_pending_attempt(message_id, attempts, self._now() + delay)
                await asyncio.sleep(delay)
            elif response.status_code >= 400:
                logger.error(
                    "DROP id=%s attempt=%d status=%d body=%s",
                    message_id,
                    attempts,
                    response.status_code,
                    response.text[:200],
                )
                self.db.remove_pending(message_id)
            else:
                logger.info(
                    "SENT id=%s from=%s lamport=%d attempt=%d",
                    message_id,
                    payload.get("from"),
                    payload.get("lamport"),
                    attempts,
                )
                self.db.remove_pending(message_id)

    def _backoff(self, attempts: int) -> float:
        delay = config.RETRY_BASE_SECONDS * (2 ** (attempts - 1))
        return min(delay, config.RETRY_MAX_SECONDS)

    @staticmethod
    def _now() -> float:
        return asyncio.get_running_loop().time()
