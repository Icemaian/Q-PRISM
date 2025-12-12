import asyncio
from dataclasses import dataclass, field
from typing import List, Tuple

from qprism.transport.server_shim.base_H3_shim import BaseH3Shim

@dataclass(order=True)
class _QueuedReq:
    sort_key: int
    stream_id: int = field(compare=False)
    headers: List[Tuple[bytes, bytes]] = field(compare=False)

class QPRISMServer(BaseH3Shim):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._q: asyncio.PriorityQueue[_QueuedReq] = asyncio.PriorityQueue()
        self._worker = asyncio.create_task(self._serve_queue())

    def connection_lost(self, exc):
        if self._worker:
            self._worker.cancel()
        super().connection_lost(exc)

    def _extract_urgency(self, headers: List[Tuple[bytes, bytes]]) -> int:
        h = {k: v for k, v in headers}
        raw = h.get(b"priority", b"u=7").decode(errors="ignore")
        try:
            for part in raw.split(","):
                part = part.strip()
                if part.startswith("u="):
                    u = int(part[2:])
                    return max(0, min(7, u))
        except Exception:
            pass
        return 7

    def _admit_request(self, stream_id: int, headers: List[Tuple[bytes, bytes]]) -> None:
        u = self._extract_urgency(headers)
        self._q.put_nowait(_QueuedReq(sort_key=u, stream_id=stream_id, headers=headers))

    async def _serve_queue(self) -> None:
        while True:
            req = await self._q.get()
            if self._is_cancelled(req.stream_id):
                continue
            self._tasks[req.stream_id] = asyncio.create_task(
                self._handle_request(req.stream_id, req.headers)
            )
