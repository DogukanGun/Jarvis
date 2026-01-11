/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { GeminiEventType, type ServerGeminiStreamEvent } from '@qwen-code/qwen-code-core';
import type {
  WrapperSSEEvent,
  ThoughtEvent,
  ContentEvent,
  ToolCallEvent,
  ToolResultEvent,
  ErrorEvent,
} from './types.js';

/**
 * Monitors and transforms core module events into wrapper SSE events
 */
export class EventMonitor {
  private taskId: string;
  private eventBuffer: string = '';
  private toolCallMap: Map<string, { name: string; args: Record<string, unknown> }> = new Map();

  constructor(taskId: string) {
    this.taskId = taskId;
  }

  /**
   * Transform a core event into a wrapper SSE event
   */
  transformEvent(coreEvent: ServerGeminiStreamEvent): WrapperSSEEvent | null {
    const timestamp = Date.now();

    switch (coreEvent.type) {
      case GeminiEventType.Thought: {
        const thoughtEvent: ThoughtEvent = {
          type: 'thought',
          timestamp,
          taskId: this.taskId,
          content: typeof coreEvent.value === 'string' 
            ? coreEvent.value 
            : JSON.stringify(coreEvent.value),
        };
        return thoughtEvent;
      }

      case GeminiEventType.Content: {
        // Accumulate content
        this.eventBuffer += coreEvent.value;
        
        const contentEvent: ContentEvent = {
          type: 'content',
          timestamp,
          taskId: this.taskId,
          text: coreEvent.value,
        };
        return contentEvent;
      }

      case GeminiEventType.ToolCallRequest: {
        const request = coreEvent.value;
        
        // Store tool call info for later correlation
        this.toolCallMap.set(request.callId, {
          name: request.name,
          args: request.args as Record<string, unknown>,
        });

        const toolCallEvent: ToolCallEvent = {
          type: 'tool_call',
          timestamp,
          taskId: this.taskId,
          callId: request.callId,
          name: request.name,
          args: request.args as Record<string, unknown>,
        };
        return toolCallEvent;
      }

      case GeminiEventType.ToolCallResponse: {
        const response = coreEvent.value;
        
        const toolResultEvent: ToolResultEvent = {
          type: 'tool_result',
          timestamp,
          taskId: this.taskId,
          callId: response.callId,
          result: response.resultDisplay,
          success: !response.error,
        };
        return toolResultEvent;
      }

      case GeminiEventType.Error: {
        const errorEvent: ErrorEvent = {
          type: 'error',
          timestamp,
          taskId: this.taskId,
          error: coreEvent.value.error.message || String(coreEvent.value.error),
          reason: coreEvent.value.error.status?.toString(),
        };
        return errorEvent;
      }

      case GeminiEventType.UserCancelled: {
        const cancelledEvent: ErrorEvent = {
          type: 'error',
          timestamp,
          taskId: this.taskId,
          error: 'Task cancelled by user',
          reason: 'user_cancelled',
        };
        return cancelledEvent;
      }

      case GeminiEventType.LoopDetected: {
        const loopEvent: ErrorEvent = {
          type: 'error',
          timestamp,
          taskId: this.taskId,
          error: 'Loop detected in agent behavior',
          reason: 'loop_detected',
        };
        return loopEvent;
      }

      // Events we don't transform to SSE
      case GeminiEventType.Retry:
      case GeminiEventType.ChatCompressed:
      case GeminiEventType.ToolCallConfirmation:
      case GeminiEventType.Citation:
      case GeminiEventType.Finished:
      case GeminiEventType.MaxSessionTurns:
      case GeminiEventType.SessionTokenLimitExceeded:
        return null;

      default:
        // Unknown event type, log for debugging
        console.log('Unknown core event type:', (coreEvent as any).type);
        return null;
    }
  }

  /**
   * Get accumulated content buffer
   */
  getContentBuffer(): string {
    return this.eventBuffer;
  }

  /**
   * Clear content buffer
   */
  clearContentBuffer(): void {
    this.eventBuffer = '';
  }

  /**
   * Get tool call info by call ID
   */
  getToolCallInfo(callId: string): { name: string; args: Record<string, unknown> } | undefined {
    return this.toolCallMap.get(callId);
  }

  /**
   * Clear tool call map
   */
  clearToolCallMap(): void {
    this.toolCallMap.clear();
  }
}

