"""
WebSocket Connection Manager — Netflix Real-Time Standard.

Manages active WebSocket connections per company with bounded concurrency.
Thread-safe using asyncio.Lock (single event loop, no threading primitives needed).
"""

import asyncio
from collections import defaultdict

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

MAX_CONNECTIONS_PER_COMPANY = 50
POLICY_VIOLATION_CODE = 1008


class ConnectionManager:
    """Singleton registry of active WebSocket connections keyed by company_id.

    Uses asyncio.Lock to protect the shared connection sets.  Dead connections
    are pruned lazily during broadcast so normal-path performance is O(1).
    """

    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, company_id: int) -> bool:
        """Accept and register the connection if the per-company cap is not reached.

        Returns False (and closes with 1008 Policy Violation) when the company
        has hit MAX_CONNECTIONS_PER_COMPANY; returns True on success.
        """
        async with self._lock:
            if len(self.active_connections[company_id]) >= MAX_CONNECTIONS_PER_COMPANY:
                await websocket.close(code=POLICY_VIOLATION_CODE)
                logger.warning(
                    "websocket_connection_rejected",
                    company_id=company_id,
                    reason="max_connections_reached",
                    limit=MAX_CONNECTIONS_PER_COMPANY,
                )
                return False
            await websocket.accept()
            self.active_connections[company_id].add(websocket)
            logger.info(
                "websocket_accepted",
                company_id=company_id,
                total=len(self.active_connections[company_id]),
            )
            return True

    async def disconnect(self, websocket: WebSocket, company_id: int) -> None:
        """Remove a connection from the registry.

        Uses discard() so calling this multiple times is idempotent.
        """
        async with self._lock:
            self.active_connections[company_id].discard(websocket)
            logger.info(
                "websocket_disconnected",
                company_id=company_id,
                remaining=len(self.active_connections[company_id]),
            )

    async def broadcast_to_company(self, company_id: int, message: dict) -> None:
        """Broadcast a JSON payload to every active connection for a company.

        Dead connections (send failure) are collected outside the lock to
        minimise lock-hold time, then pruned in a second lock acquisition.
        This prevents blocking new connects/disconnects during slow I/O.
        """
        if company_id not in self.active_connections:
            return

        async with self._lock:
            connections = self.active_connections[company_id].copy()

        stale: set[WebSocket] = set()
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.add(ws)

        if stale:
            async with self._lock:
                self.active_connections[company_id] -= stale
            logger.info(
                "websocket_stale_pruned",
                company_id=company_id,
                pruned=len(stale),
            )


manager = ConnectionManager()
