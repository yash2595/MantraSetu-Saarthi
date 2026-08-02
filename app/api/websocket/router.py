"""WebSocket frame router definition for Module 4 Transport Layer with state machine and flow control."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies.voice import get_tts_pipeline, get_voice_gateway
from app.api.metrics import transport_metrics
from app.api.schemas.websocket import ProtocolMessageType, WebSocketEnvelope
from app.api.websocket.state_machine import (
    ConnectionState,
    InvalidStateTransition,
    WebSocketStateMachine,
)
from app.schemas.api.interaction import InteractionRequest
from app.voice.gateway import VoiceGateway
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["WebSocket Stream"])


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Enterprise bidirectional WebSocket streaming endpoint with state machine and atomic backpressure."""
    await websocket.accept()
    transport_metrics.record_ws_connect()

    state_machine = WebSocketStateMachine(initial_state=ConnectionState.CONNECTING)
    voice_gateway: VoiceGateway = get_voice_gateway()
    tts_pipeline: VoiceResponsePipeline = get_tts_pipeline()

    active_session_id: str | None = None
    outbound_queue: asyncio.Queue[WebSocketEnvelope] = asyncio.Queue(maxsize=100)

    logger.info("WebSocket connection accepted", extra={"client": websocket.client.host if websocket.client else "unknown"})

    async def sender_task() -> None:
        """Background worker consuming bounded outbound queue to enforce flow control."""
        try:
            while True:
                outbound_frame = await outbound_queue.get()
                await websocket.send_text(outbound_frame.model_dump_json())
                outbound_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as send_err:
            logger.error("Error in outbound WebSocket sender task", extra={"error": str(send_err)})

    sender_worker = asyncio.create_task(sender_task())

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                frame = WebSocketEnvelope.model_validate_json(raw_text)
            except Exception as parse_err:
                err_reply = WebSocketEnvelope(
                    type=ProtocolMessageType.ERROR,
                    payload={"message": f"Invalid frame payload: {str(parse_err)}"},
                )
                try:
                    outbound_queue.put_nowait(err_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()
                continue

            # Validate frame type against active connection state
            if frame.type == ProtocolMessageType.AUDIO_FRAME and state_machine.current_state not in (
                ConnectionState.CONNECTED,
                ConnectionState.STREAMING,
            ):
                err_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    type=ProtocolMessageType.ERROR,
                    payload={"message": f"Cannot process AUDIO_FRAME in state '{state_machine.current_state.value}'."},
                )
                try:
                    outbound_queue.put_nowait(err_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()
                continue

            if frame.type == ProtocolMessageType.CONNECT:
                try:
                    state_machine.transition_to(ConnectionState.CONNECTED, reason="connect_frame_received")
                except InvalidStateTransition as st_err:
                    err_reply = WebSocketEnvelope(
                        request_id=frame.request_id,
                        type=ProtocolMessageType.ERROR,
                        payload={"message": str(st_err)},
                    )
                    try:
                        outbound_queue.put_nowait(err_reply)
                    except asyncio.QueueFull:
                        transport_metrics.record_dropped_frame()
                    continue

                session = await voice_gateway.start_voice_session(
                    connection_id=f"ws-conn-{uuid4().hex[:8]}",
                    conversation_id=frame.conversation_id,
                    language=frame.payload.get("language", "hi"),
                )
                active_session_id = session.session_id
                reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.CONNECTED,
                    payload={"status": "connected", "session_id": active_session_id},
                )
                try:
                    outbound_queue.put_nowait(reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

            elif frame.type == ProtocolMessageType.TEXT:
                if not active_session_id:
                    session = await voice_gateway.start_voice_session("ws-temp-conn")
                    active_session_id = session.session_id
                    state_machine.transition_to(ConnectionState.CONNECTED, reason="implicit_text_session")

                state_machine.transition_to(ConnectionState.PROCESSING, reason="processing_text_query")

                resp = await voice_gateway.ai_orchestrator.process(
                    request=InteractionRequest(
                        conversation_id=frame.conversation_id,
                        session_id=active_session_id,
                        user_input=frame.payload.get("text", ""),
                    )
                )

                state_machine.transition_to(ConnectionState.RESPONDING, reason="text_orchestration_complete")

                ai_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": resp.content,
                        "intent": resp.intent.name if hasattr(resp.intent, "name") else (str(resp.intent) if resp.intent else None),
                    },
                )
                try:
                    outbound_queue.put_nowait(ai_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

                # Stream audio chunks from TTS pipeline
                async for chunk in tts_pipeline.process_response(resp):
                    audio_reply = WebSocketEnvelope(
                        request_id=frame.request_id,
                        session_id=active_session_id,
                        conversation_id=frame.conversation_id,
                        type=ProtocolMessageType.AUDIO_CHUNK,
                        payload={
                            "sequence_number": chunk.sequence_number,
                            "is_final": chunk.is_final,
                            "data_length": len(chunk.data),
                        },
                    )
                    try:
                        outbound_queue.put_nowait(audio_reply)
                    except asyncio.QueueFull:
                        transport_metrics.record_dropped_frame()

                state_machine.transition_to(ConnectionState.IDLE, reason="response_streaming_complete")

            elif frame.type == ProtocolMessageType.PING:
                pong = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    type=ProtocolMessageType.PONG,
                )
                try:
                    outbound_queue.put_nowait(pong)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

            elif frame.type == ProtocolMessageType.DISCONNECT:
                state_machine.transition_to(ConnectionState.DISCONNECTED, reason="client_requested_disconnect")
                if active_session_id:
                    await voice_gateway.session_manager.close_session(active_session_id)
                    active_session_id = None
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client", extra={"session_id": active_session_id})
    finally:
        state_machine.transition_to(ConnectionState.DISCONNECTED, reason="connection_cleanup")
        transport_metrics.record_ws_disconnect()

        # Graceful Outbound Queue Drain before sender worker cancellation
        try:
            await outbound_queue.join()
        except Exception:
            pass

        sender_worker.cancel()
        try:
            await sender_worker
        except asyncio.CancelledError:
            pass

        if active_session_id:
            await voice_gateway.session_manager.close_session(active_session_id)
