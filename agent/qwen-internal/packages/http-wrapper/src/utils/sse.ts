/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Response } from 'express';
import type { WrapperSSEEvent } from '../types.js';

/**
 * Setup SSE connection with proper headers
 */
export function setupSSE(res: Response): void {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no', // Disable buffering in nginx
  });

  // Send initial comment to establish connection
  res.write(': connected\n\n');
}

/**
 * Send an SSE event to the client
 */
export function sendSSEEvent(res: Response, event: WrapperSSEEvent): void {
  try {
    const eventName = event.type;
    const data = JSON.stringify(event);

    // SSE format: event: <event_name>\ndata: <json_data>\n\n
    res.write(`event: ${eventName}\n`);
    res.write(`data: ${data}\n\n`);
  } catch (error) {
    console.error('Error sending SSE event:', error);
  }
}

/**
 * Send a ping/keepalive message
 */
export function sendSSEPing(res: Response): void {
  res.write(': ping\n\n');
}

/**
 * Close SSE connection
 */
export function closeSSE(res: Response): void {
  try {
    if (!res.writableEnded) {
      res.end();
    }
  } catch (error) {
    console.error('Error closing SSE connection:', error);
  }
}

/**
 * Broadcast event to multiple SSE connections
 */
export function broadcastSSEEvent(
  connections: Set<Response>,
  event: WrapperSSEEvent,
): void {
  const disconnected: Response[] = [];

  connections.forEach((res) => {
    try {
      if (res.writableEnded) {
        disconnected.push(res);
      } else {
        sendSSEEvent(res, event);
      }
    } catch (error) {
      console.error('Error broadcasting to connection:', error);
      disconnected.push(res);
    }
  });

  // Clean up disconnected connections
  disconnected.forEach((res) => connections.delete(res));
}

/**
 * Setup periodic keepalive pings to prevent connection timeout
 */
export function setupSSEKeepalive(
  res: Response,
  intervalMs: number = 30000,
): NodeJS.Timeout {
  const interval = setInterval(() => {
    if (res.writableEnded) {
      clearInterval(interval);
    } else {
      sendSSEPing(res);
    }
  }, intervalMs);

  // Clean up on connection close
  res.on('close', () => {
    clearInterval(interval);
  });

  return interval;
}

