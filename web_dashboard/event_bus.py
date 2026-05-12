import asyncio
import time
from typing import Any, AsyncIterator, Callable, Dict, List


class EventBus:
    """
    Bus de eventos pub/sub asincrono. Desacopla Go2Connection del dashboard web.
    Los suscriptores reciben eventos por topico via AsyncIterator.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 500

    def publish(self, topic: str, data: Any):
        timestamp = time.time()
        event = {"topic": topic, "data": data, "timestamp": timestamp}
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        queues = self._subscribers.get(topic, [])
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

        for q in self._subscribers.get("*", []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe(self, topic: str) -> "EventStream":
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(queue)
        return EventStream(queue, topic, self)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_history[-limit:]


class EventStream:
    def __init__(self, queue: asyncio.Queue, topic: str, bus: EventBus):
        self._queue = queue
        self._topic = topic
        self._bus = bus

    def __aiter__(self):
        return self

    async def __anext__(self) -> Dict[str, Any]:
        return await self._queue.get()

    def close(self):
        if self._topic in self._bus._subscribers:
            queues = self._bus._subscribers[self._topic]
            if self._queue in queues:
                queues.remove(self._queue)
            if not queues:
                del self._bus._subscribers[self._topic]
