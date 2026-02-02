/**
 * WebSocket Gateway for connecting to Observation Hub
 */

import { io, Socket } from 'socket.io-client';
import { eventBus } from './event-bus.js';
import type {
  TaskCreatedPayload,
  TaskUpdatedPayload,
  EventPayload,
} from './event-bus.js';

export interface GatewayConfig {
  hubUrl: string;
  agentId: string;
  agentName?: string;
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
}

/**
 * WebSocket Gateway that connects agent to observation hub
 */
export class WebSocketGateway {
  private socket: Socket | null = null;
  private config: GatewayConfig;
  private connected: boolean = false;

  constructor(config: GatewayConfig) {
    this.config = {
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      ...config,
    };
  }

  /**
   * Connect to the observation hub
   */
  connect(): void {
    if (this.socket) {
      console.log('[Gateway] Already connected or connecting');
      return;
    }

    console.log(`[Gateway] Connecting to observation hub at ${this.config.hubUrl}`);

    this.socket = io(this.config.hubUrl, {
      path: '/ws',
      reconnection: this.config.reconnection,
      reconnectionAttempts: this.config.reconnectionAttempts,
      reconnectionDelay: this.config.reconnectionDelay,
      auth: {
        agentId: this.config.agentId,
        agentName: this.config.agentName,
      },
    });

    this.setupSocketListeners();
    this.setupEventBusListeners();
  }

  /**
   * Setup socket event listeners
   */
  private setupSocketListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      this.connected = true;
      console.log(`[Gateway] Connected to observation hub as ${this.config.agentId}`);

      // Register agent with hub
      this.socket?.emit('agent_register', {
        agentId: this.config.agentId,
        agentName: this.config.agentName,
      });
    });

    this.socket.on('disconnect', (reason) => {
      this.connected = false;
      console.log(`[Gateway] Disconnected from observation hub: ${reason}`);
    });

    this.socket.on('connect_error', (error) => {
      console.error(`[Gateway] Connection error: ${error.message}`);
    });

    // Handle answer responses from hub (forwarded from phone)
    this.socket.on('answer_question', (data: { taskId: string; answer: string }) => {
      console.log(`[Gateway] Received answer for task ${data.taskId}`);
      // This will be handled by the task manager through a callback
      this.onAnswerReceived?.(data.taskId, data.answer);
    });

    // Handle task cancellation from hub
    this.socket.on('cancel_task', (data: { taskId: string }) => {
      console.log(`[Gateway] Received cancel request for task ${data.taskId}`);
      this.onCancelReceived?.(data.taskId);
    });
  }

  /**
   * Setup event bus listeners to forward events to hub
   */
  private setupEventBusListeners(): void {
    eventBus.on('task_created', (payload: TaskCreatedPayload) => {
      this.emit('task_created', payload);
    });

    eventBus.on('task_updated', (payload: TaskUpdatedPayload) => {
      this.emit('task_updated', payload);
    });

    eventBus.on('task_deleted', (taskId: string) => {
      this.emit('task_deleted', { taskId, agentId: this.config.agentId });
    });

    eventBus.on('new_event', (payload: EventPayload) => {
      this.emit('new_event', payload);
    });
  }

  /**
   * Emit event to observation hub
   */
  private emit(event: string, data: unknown): void {
    if (!this.socket || !this.connected) {
      console.log(`[Gateway] Not connected, queuing event: ${event}`);
      return;
    }

    this.socket.emit(event, data);
  }

  /**
   * Disconnect from the observation hub
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      console.log('[Gateway] Disconnected from observation hub');
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connected;
  }

  /**
   * Get agent ID
   */
  getAgentId(): string {
    return this.config.agentId;
  }

  // Callbacks for handling messages from hub
  onAnswerReceived?: (taskId: string, answer: string) => void;
  onCancelReceived?: (taskId: string) => void;
}

// Singleton instance - initialized when agent starts
let gatewayInstance: WebSocketGateway | null = null;

/**
 * Initialize the WebSocket gateway
 */
export function initializeGateway(config: GatewayConfig): WebSocketGateway {
  if (gatewayInstance) {
    console.log('[Gateway] Gateway already initialized');
    return gatewayInstance;
  }

  gatewayInstance = new WebSocketGateway(config);
  return gatewayInstance;
}

/**
 * Get the gateway instance
 */
export function getGateway(): WebSocketGateway | null {
  return gatewayInstance;
}

/**
 * Get the agent ID from environment or gateway
 */
export function getAgentId(): string {
  return gatewayInstance?.getAgentId() || process.env['AGENT_ID'] || 'qwen-default';
}
