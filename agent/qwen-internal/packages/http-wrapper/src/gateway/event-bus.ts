/**
 * Event Bus for bridging TaskManager events to WebSocket Gateway
 */

import { EventEmitter } from 'events';
import type { WrapperSSEEvent, TaskState, TaskStatus } from '../types.js';

/**
 * Event types emitted by the event bus
 */
export interface EventBusEvents {
  task_created: (task: TaskCreatedPayload) => void;
  task_updated: (task: TaskUpdatedPayload) => void;
  task_deleted: (taskId: string) => void;
  new_event: (event: EventPayload) => void;
}

export interface TaskCreatedPayload {
  taskId: string;
  agentId: string;
  description: string;
  status: TaskStatus;
  createdAt: number;
}

export interface TaskUpdatedPayload {
  taskId: string;
  agentId: string;
  status: TaskStatus;
  startedAt?: number;
  completedAt?: number;
  result?: string;
  error?: string;
}

export interface EventPayload {
  taskId: string;
  agentId: string;
  event: WrapperSSEEvent;
}

/**
 * Typed event emitter for internal event bus
 */
class TypedEventEmitter extends EventEmitter {
  override emit<K extends keyof EventBusEvents>(
    event: K,
    ...args: Parameters<EventBusEvents[K]>
  ): boolean {
    return super.emit(event, ...args);
  }

  override on<K extends keyof EventBusEvents>(
    event: K,
    listener: EventBusEvents[K],
  ): this {
    return super.on(event, listener);
  }

  override off<K extends keyof EventBusEvents>(
    event: K,
    listener: EventBusEvents[K],
  ): this {
    return super.off(event, listener);
  }
}

/**
 * Singleton event bus instance
 */
export const eventBus = new TypedEventEmitter();
eventBus.setMaxListeners(100); // Allow many listeners for multiple subscriptions
