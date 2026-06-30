import asyncio

from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.digital_twin.simulator import digital_twin
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/twin")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)

    try:

        while True:

            await manager.broadcast(
                digital_twin.get_state()
            )

            await asyncio.sleep(1)

    except WebSocketDisconnect:

        manager.disconnect(websocket)