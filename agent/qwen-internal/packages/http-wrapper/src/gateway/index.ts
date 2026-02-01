/**
 * Gateway module exports
 */

export { eventBus } from './event-bus.js';
export type {
  EventBusEvents,
  TaskCreatedPayload,
  TaskUpdatedPayload,
  EventPayload,
} from './event-bus.js';

export {
  WebSocketGateway,
  initializeGateway,
  getGateway,
  getAgentId,
} from './websocket-gateway.js';
export type { GatewayConfig } from './websocket-gateway.js';
