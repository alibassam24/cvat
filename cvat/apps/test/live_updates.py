# SPDX-License-Identifier: MIT

"""
Live label counts over WebSocket.

Annotation writes end with task.touch() (see dataset_manager JobAnnotation), which
saves the Task. A post_save receiver publishes the task id to Redis once the
transaction commits. Redis rather than an in-process queue, because imports run in
RQ worker processes, not in the server.

Each socket subscribes to its task's channel. On connect and after every change it
calls the REST endpoint in-process with the client's own cookies and headers, and
sends the JSON body as is. So every message is a full snapshot (a client that missed
messages while disconnected is correct again after the first one), and login and the
task "view" policy are checked by exactly the same code as the REST endpoint, on every
push, not only when the socket opens.
"""

import asyncio
import re
from urllib.parse import urlsplit

import redis
import redis.asyncio
from django.conf import settings

from cvat.apps.engine.renderers import CVATAPIRenderer

SOCKET_PATH = re.compile(r"^/api/test/tasks/(?P<task_id>\d+)/label-counts/ws$")
# Several saves in a row (a task import touches the task once per job) become one push.
DEBOUNCE_SECONDS = 0.3
# Close codes 4000 + HTTP status tell the client whether retrying makes sense.
CLOSE_CODE_BASE = 4000
CLOSE_CODE_INTERNAL_ERROR = 1011
# Headers that describe the WebSocket handshake itself, not the client.
HANDSHAKE_HEADERS = {
    b"upgrade",
    b"connection",
    b"sec-websocket-key",
    b"sec-websocket-version",
    b"sec-websocket-extensions",
    b"sec-websocket-protocol",
}


def channel_name(task_id: int) -> str:
    return f"label-counts:task:{task_id}"


def _redis_kwargs() -> dict:
    return {
        "host": settings.REDIS_INMEM_SETTINGS["HOST"],
        "port": settings.REDIS_INMEM_SETTINGS["PORT"],
        "password": settings.REDIS_INMEM_SETTINGS["PASSWORD"] or None,
    }


def publish_task_changed(task_id: int) -> None:
    with redis.Redis(**_redis_kwargs()) as client:
        client.publish(channel_name(task_id), "changed")


def _is_same_origin(scope) -> bool:
    # Browsers send cookies with cross-site WebSocket handshakes, so without this check
    # any page the user visits could read their counts. Non-browser clients send no Origin.
    headers = dict(scope["headers"])
    origin = headers.get(b"origin")
    if origin is None:
        return True
    return urlsplit(origin.decode("latin-1")).netloc == headers.get(b"host", b"").decode("latin-1")


async def _fetch_counts(django_app, ws_scope, task_id: int) -> tuple[int, bytes]:
    """Run GET .../label-counts through the full Django stack as the socket's client."""
    path = f"/api/test/tasks/{task_id}/label-counts"
    client_headers = [
        (name, value) for name, value in ws_scope["headers"] if name not in HANDSHAKE_HEADERS
    ]
    http_scope = {
        "type": "http",
        "asgi": ws_scope.get("asgi", {"version": "3.0"}),
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https" if ws_scope.get("scheme") == "wss" else "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": ws_scope.get("query_string", b""),
        "root_path": ws_scope.get("root_path", ""),
        "headers": [*client_headers, (b"accept", CVATAPIRenderer.media_type.encode())],
        "client": ws_scope.get("client"),
        "server": ws_scope.get("server"),
    }

    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        # Django keeps listening for a disconnect while it responds; there won't be one.
        await asyncio.Event().wait()

    status = None
    body = []

    async def send(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            body.append(message.get("body", b""))

    await django_app(http_scope, receive, send)
    return status, b"".join(body)


class _LabelCountsSocket:
    def __init__(self, django_app, scope, receive, send, task_id: int):
        self.django_app = django_app
        self.scope = scope
        self.receive = receive
        self.send = send
        self.task_id = task_id

    async def _close(self, code: int) -> None:
        await self.send({"type": "websocket.close", "code": code})

    async def _push_snapshot(self) -> bool:
        status, body = await _fetch_counts(self.django_app, self.scope, self.task_id)
        if status != 200:
            await self._close(CLOSE_CODE_BASE + status)
            return False
        await self.send({"type": "websocket.send", "text": body.decode()})
        return True

    async def _wait_for_disconnect(self) -> None:
        while (await self.receive())["type"] != "websocket.disconnect":
            pass  # the client has nothing to say, anything it sends is ignored

    async def _listen(self, changed: asyncio.Event) -> None:
        client = redis.asyncio.Redis(**_redis_kwargs())
        try:
            async with client.pubsub() as pubsub:
                await pubsub.subscribe(channel_name(self.task_id))
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        changed.set()
        finally:
            await client.aclose()

    async def _push_changes(self, changed: asyncio.Event) -> None:
        while True:
            await changed.wait()
            await asyncio.sleep(DEBOUNCE_SECONDS)
            changed.clear()
            if not await self._push_snapshot():
                return

    async def run(self) -> None:
        if (await self.receive())["type"] != "websocket.connect":
            return
        # Accept first so the close code reaches the browser; a refused handshake is just 1006.
        await self.send({"type": "websocket.accept"})
        if not _is_same_origin(self.scope):
            await self._close(CLOSE_CODE_BASE + 403)
            return

        changed = asyncio.Event()
        listener = asyncio.create_task(self._listen(changed))
        if not await self._push_snapshot():
            listener.cancel()
            return

        tasks = {
            listener,
            asyncio.create_task(self._push_changes(changed)),
            asyncio.create_task(self._wait_for_disconnect()),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        if listener in done and listener.exception():
            # Lost Redis: close so the client reconnects and resubscribes.
            await self._close(CLOSE_CODE_INTERNAL_ERROR)


def with_label_counts_sockets(django_app):
    """ASGI wrapper: serves the label counts socket, passes everything else to Django."""

    async def application(scope, receive, send):
        if scope["type"] == "websocket" and (match := SOCKET_PATH.match(scope["path"])):
            await _LabelCountsSocket(django_app, scope, receive, send, int(match["task_id"])).run()
        else:
            await django_app(scope, receive, send)

    return application
