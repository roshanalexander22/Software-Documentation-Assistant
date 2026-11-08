---
doc_id: DOC-FA-007
title: Streaming Responses, Server-Sent Events (SSE), and WebSockets
version: v0.115
framework: FastAPI
category: Realtime & Streaming
tags: [streaming, websockets, sse, async, chunks, realtime]
source_url: https://fastapi.tiangolo.com/advanced/custom-response/
---

# Streaming Responses, Server-Sent Events (SSE), and WebSockets

Modern API architectures frequently require real-time bidirectional communication or streamed token delivery (such as streaming generative AI LLM responses). FastAPI supports both streaming HTTP responses and native WebSockets.

## Streaming HTTP Responses (LLM & Big Data)

`StreamingResponse` transmits data chunks using standard HTTP chunked transfer encoding without keeping the entire payload in server memory:

```python
import asyncio
from typing import AsyncIterable
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="Streaming API", version="0.115.0")

async def fake_llm_token_generator(prompt: str) -> AsyncIterable[str]:
    response_words = f"Generated answer for prompt: {prompt}. Streamed token by token.".split()
    for word in response_words:
        await asyncio.sleep(0.08)
        yield f"data: {word}\n\n"

@app.get("/stream-tokens")
async def stream_tokens(prompt: str = "Explain RAG"):
    """
    Returns an SSE (Server-Sent Events) compliant stream.
    Clients can consume with EventSource in Javascript.
    """
    return StreamingResponse(
        fake_llm_token_generator(prompt),
        media_type="text/event-stream"
    )
```

## Bidirectional WebSockets

For two-way persistent socket connections, FastAPI exposes the `@app.websocket` decorator:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} disconnected.")
```

