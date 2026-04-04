"""
WebSocket endpoint — real-time event stream per company.

Connects to Redis pub/sub channel `quantyx:events:{company_id}` and forwards
all published JSON messages to the authenticated browser tab.  A 30-second
heartbeat prevents idle-connection timeouts at load-balancer layer.

Auth note: WebSocket upgrade requests cannot carry Authorization headers in
browsers, so the JWT is passed as a query param and validated here manually.
"""

import asyncio

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.config import settings
from app.core.security import decode_token
from app.utils.ws_connection_manager import manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])

HEARTBEAT_INTERVAL_SECONDS = 30
ACCESS_TOKEN_TYPE = "access"


@router.websocket("/ws/company/{company_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    company_id: int,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """Stream real-time fraud and transaction events to an authenticated client.

    Validates the JWT token, enforces company_id isolation, then subscribes to
    Redis pub/sub and forwards all messages. A heartbeat task pings the client
    every 30 s — clients are expected to ignore ping frames silently.
    """
    # --- Auth gate (cannot use HTTPBearer middleware for WebSocket upgrades) ---
    try:
        payload = decode_token(token)
        token_type: str = payload.get("type", "")
        token_company: int = int(payload.get("company_id", -1))
        if token_type != ACCESS_TOKEN_TYPE or token_company != company_id:
            await websocket.close(code=1008)
            logger.warning(
                "websocket_auth_rejected",
                company_id=company_id,
                reason="company_mismatch_or_wrong_type",
            )
            return
    except (JWTError, Exception) as exc:
        await websocket.close(code=1008)
        logger.warning(
            "websocket_auth_failed",
            company_id=company_id,
            error=str(exc),
        )
        return

    connected = await manager.connect(websocket, company_id)
    if not connected:
        return

    redis_client: aioredis.Redis = aioredis.from_url(
        settings.REDIS_URL, decode_responses=True
    )
    pubsub = redis_client.pubsub()
    channel = f"quantyx:events:{company_id}"
    await pubsub.subscribe(channel)

    logger.info("websocket_session_started", company_id=company_id, channel=channel)

    async def heartbeat() -> None:
        """Ping every 30 s to keep the connection alive through idle timeouts.

        The client-side useWebSocket hook silently drops ping frames so they
        have zero UX cost.  Task is cancelled in the finally block below.
        """
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(
            "websocket_stream_error",
            company_id=company_id,
            error=str(exc),
        )
    finally:
        heartbeat_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass
        try:
            await redis_client.aclose()
        except Exception:
            pass
        await manager.disconnect(websocket, company_id)
        logger.info("websocket_session_ended", company_id=company_id)
