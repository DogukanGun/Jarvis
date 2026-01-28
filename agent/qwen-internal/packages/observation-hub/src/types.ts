/**
 * Type definitions for Observation Hub
 */

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'waiting_for_answer'
  | 'completed'
  | 'error'
  | 'cancelled';

export type EventType =
  | 'thought'
  | 'content'
  | 'tool_call'
  | 'tool_result'
  | 'question'
  | 'completed'
  | 'error'
  | 'status';

/**
 * Connected agent information
 */
export interface ConnectedAgent {
  id: string;
  name?: string;
  socketId: string;
  status: 'online' | 'offline';
  lastSeen: Date;
  activeTasks: number;
}

/**
 * Task created payload from agent
 */
export interface TaskCreatedPayload {
  taskId: string;
  agentId: string;
  description: string;
  status: TaskStatus;
  createdAt: number;
}

/**
 * Task updated payload from agent
 */
export interface TaskUpdatedPayload {
  taskId: string;
  agentId: string;
  status: TaskStatus;
  startedAt?: number;
  completedAt?: number;
  result?: string;
  error?: string;
}

/**
 * Event payload from agent
 */
export interface EventPayload {
  taskId: string;
  agentId: string;
  event: {
    type: EventType;
    timestamp: number;
    taskId: string;
    agentId: string;
    [key: string]: unknown;
  };
}

/**
 * Task info for API responses
 */
export interface TaskInfo {
  id: string;
  agentId: string;
  description: string;
  status: TaskStatus;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  result?: string;
  error?: string;
}

/**
 * Event info for API responses
 */
export interface EventInfo {
  id: string;
  taskId: string;
  type: EventType;
  data: Record<string, unknown>;
  timestamp: Date;
}

/**
 * WebSocket client-to-server events
 */
export interface ClientToServerEvents {
  join_all: () => void;
  join_agent: (agentId: string) => void;
  join_task: (taskId: string) => void;
  leave_all: () => void;
  leave_agent: (agentId: string) => void;
  leave_task: (taskId: string) => void;
}

/**
 * WebSocket server-to-client events
 */
export interface ServerToClientEvents {
  agent_connected: (agent: ConnectedAgent) => void;
  agent_disconnected: (agentId: string) => void;
  task_created: (task: TaskInfo) => void;
  task_updated: (task: TaskInfo) => void;
  new_event: (event: EventInfo) => void;
}

/**
 * Agent-to-hub events
 */
export interface AgentToHubEvents {
  agent_register: (data: { agentId: string; agentName?: string }) => void;
  task_created: (payload: TaskCreatedPayload) => void;
  task_updated: (payload: TaskUpdatedPayload) => void;
  task_deleted: (data: { taskId: string; agentId: string }) => void;
  new_event: (payload: EventPayload) => void;
}
