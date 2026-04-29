from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisBus:
    """Tiny wrapper around redis-py async: pub/sub fan-out + leader lock."""

    LEADER_KEY = "fleet:leader"
    LEADER_INFO_KEY = "fleet:leader:info"

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Any | None = None

    async def connect(self) -> None:
        client: Any = aioredis.from_url(self._url, decode_responses=True)
        await client.ping()
        self._client = client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Redis not connected")
        return self._client

    async def ping(self) -> bool:
        try:
            await self.client.ping()
            return True
        except Exception:
            logger.exception("redis ping failed")
            return False

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self.client.publish(channel, json.dumps(payload, default=str))

    async def subscribe(self, *channels: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg is None:
                    continue
                data = msg.get("data")
                if not isinstance(data, str):
                    continue
                try:
                    yield {"channel": msg["channel"], "data": json.loads(data)}
                except json.JSONDecodeError:
                    continue
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    async def acquire_leader(self, instance_id: str, ttl_s: int) -> bool:
        ok = await self.client.set(self.LEADER_KEY, instance_id, nx=True, ex=ttl_s)
        if ok:
            await self.client.set(self.LEADER_INFO_KEY, instance_id, ex=ttl_s)
        return bool(ok)

    async def refresh_leader(self, instance_id: str, ttl_s: int) -> bool:
        # Lua script: only refresh if we still own the lock.
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
          redis.call('PEXPIRE', KEYS[1], ARGV[2])
          redis.call('SET', KEYS[2], ARGV[1], 'PX', ARGV[2])
          return 1
        else
          return 0
        end
        """
        res = await self.client.eval(
            script, 2, self.LEADER_KEY, self.LEADER_INFO_KEY, instance_id, str(ttl_s * 1000)
        )
        return bool(res == 1)

    async def release_leader(self, instance_id: str) -> None:
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
          redis.call('DEL', KEYS[1])
          redis.call('DEL', KEYS[2])
        end
        """
        await self.client.eval(
            script, 2, self.LEADER_KEY, self.LEADER_INFO_KEY, instance_id
        )

    async def current_leader(self) -> str | None:
        v = await self.client.get(self.LEADER_INFO_KEY)
        return v if isinstance(v, str) else None


class LeaderElector:
    """Background task: tries to become leader and refreshes the lock."""

    def __init__(
        self,
        bus: RedisBus,
        *,
        instance_id: str,
        ttl_s: int,
        refresh_s: float,
    ) -> None:
        self._bus = bus
        self._instance_id = instance_id
        self._ttl_s = ttl_s
        self._refresh_s = refresh_s
        self._is_leader = False
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    @property
    def is_leader(self) -> bool:
        return self._is_leader

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="leader-elector")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None
        if self._is_leader:
            try:
                await self._bus.release_leader(self._instance_id)
            except Exception:
                logger.exception("failed to release leader on shutdown")

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                if self._is_leader:
                    ok = await self._bus.refresh_leader(self._instance_id, self._ttl_s)
                    if not ok:
                        logger.warning("lost leadership")
                        self._is_leader = False
                else:
                    ok = await self._bus.acquire_leader(self._instance_id, self._ttl_s)
                    if ok:
                        logger.info("acquired leadership: %s", self._instance_id)
                        self._is_leader = True
            except Exception:
                logger.exception("leader elector iteration failed")
                self._is_leader = False
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=self._refresh_s)
