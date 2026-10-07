// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState } from 'react';
import { getCore } from 'cvat-core-wrapper';

const core = getCore();

export type LiveStatus = 'connecting' | 'live' | 'reconnecting' | 'stopped';

const FIRST_RETRY_MS = 1000;
const MAX_RETRY_MS = 30000;

// The server closes with 4000 + HTTP status when it refuses the client (401, 403, 404).
// Retrying can't fix those, anything else (server restart, network drop) can.
function isRefusal(code: number): boolean {
    return code >= 4400 && code < 4500;
}

function socketUrl(taskId: number, organizationSlug: string): string {
    const url = new URL(`${core.config.backendAPI}/test/tasks/${taskId}/label-counts/ws`, window.location.href);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    // Browsers can't set headers on a WebSocket, so the organization goes in the query like other requests.
    url.searchParams.set('org', organizationSlug);
    return url.toString();
}

/**
 * Keeps a socket open for the task and calls onSnapshot with every counts message.
 * Every message is a full snapshot, so after a reconnect the first message makes the
 * page correct again, whatever was missed while offline.
 */
export default function useLiveLabelCounts<T>(
    taskId: number,
    organizationSlug: string,
    onSnapshot: (counts: T) => void,
): LiveStatus {
    const [status, setStatus] = useState<LiveStatus>('connecting');
    const onSnapshotRef = useRef(onSnapshot);
    onSnapshotRef.current = onSnapshot;

    useEffect(() => {
        let socket: WebSocket | null = null;
        let retryTimer: number | undefined;
        let failedAttempts = 0;
        let disposed = false;

        const connect = (): void => {
            window.clearTimeout(retryTimer);
            setStatus(failedAttempts ? 'reconnecting' : 'connecting');
            socket = new WebSocket(socketUrl(taskId, organizationSlug));
            socket.onopen = () => {
                failedAttempts = 0;
                setStatus('live');
            };
            socket.onmessage = (event: MessageEvent<string>) => {
                onSnapshotRef.current(JSON.parse(event.data));
            };
            socket.onclose = (event: CloseEvent) => {
                socket = null;
                if (disposed) {
                    return;
                }
                if (isRefusal(event.code)) {
                    setStatus('stopped');
                    return;
                }
                // Exponential backoff with jitter, so many open pages don't reconnect in lockstep
                // after a server restart.
                const delay = Math.min(MAX_RETRY_MS, FIRST_RETRY_MS * 2 ** failedAttempts) * (0.5 + Math.random() / 2);
                failedAttempts += 1;
                setStatus('reconnecting');
                retryTimer = window.setTimeout(connect, delay);
            };
        };

        // Don't sit out the backoff when the browser tells us the network is back.
        const reconnectNow = (): void => {
            if (!socket) {
                connect();
            }
        };

        window.addEventListener('online', reconnectNow);
        connect();

        return () => {
            disposed = true;
            window.clearTimeout(retryTimer);
            window.removeEventListener('online', reconnectNow);
            socket?.close();
        };
    }, [taskId, organizationSlug]);

    return status;
}
