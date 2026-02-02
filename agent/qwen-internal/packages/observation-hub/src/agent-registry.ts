/**
 * Agent Registry for tracking connected Qwen agents
 */

import type { ConnectedAgent } from './types.js';

/**
 * Registry for managing connected agents
 */
export class AgentRegistry {
  private agents: Map<string, ConnectedAgent> = new Map();

  /**
   * Register a new agent
   */
  register(agentId: string, socketId: string, name?: string): ConnectedAgent {
    const existing = this.agents.get(agentId);

    const agent: ConnectedAgent = {
      id: agentId,
      name: name || existing?.name,
      socketId,
      status: 'online',
      lastSeen: new Date(),
      activeTasks: existing?.activeTasks ?? 0,
    };

    this.agents.set(agentId, agent);
    console.log(`[Registry] Agent registered: ${agentId} (socket: ${socketId})`);

    return agent;
  }

  /**
   * Unregister an agent by socket ID
   */
  unregisterBySocketId(socketId: string): ConnectedAgent | undefined {
    for (const [agentId, agent] of this.agents) {
      if (agent.socketId === socketId) {
        agent.status = 'offline';
        agent.lastSeen = new Date();
        console.log(`[Registry] Agent disconnected: ${agentId}`);
        return agent;
      }
    }
    return undefined;
  }

  /**
   * Get agent by ID
   */
  get(agentId: string): ConnectedAgent | undefined {
    return this.agents.get(agentId);
  }

  /**
   * Get agent by socket ID
   */
  getBySocketId(socketId: string): ConnectedAgent | undefined {
    for (const agent of this.agents.values()) {
      if (agent.socketId === socketId) {
        return agent;
      }
    }
    return undefined;
  }

  /**
   * Get all agents
   */
  getAll(): ConnectedAgent[] {
    return Array.from(this.agents.values());
  }

  /**
   * Get online agents
   */
  getOnline(): ConnectedAgent[] {
    return Array.from(this.agents.values()).filter(a => a.status === 'online');
  }

  /**
   * Update agent's last seen time
   */
  updateLastSeen(agentId: string): void {
    const agent = this.agents.get(agentId);
    if (agent) {
      agent.lastSeen = new Date();
    }
  }

  /**
   * Increment active task count for an agent
   */
  incrementActiveTasks(agentId: string): void {
    const agent = this.agents.get(agentId);
    if (agent) {
      agent.activeTasks++;
    }
  }

  /**
   * Decrement active task count for an agent
   */
  decrementActiveTasks(agentId: string): void {
    const agent = this.agents.get(agentId);
    if (agent && agent.activeTasks > 0) {
      agent.activeTasks--;
    }
  }

  /**
   * Check if agent exists and is online
   */
  isOnline(agentId: string): boolean {
    const agent = this.agents.get(agentId);
    return agent?.status === 'online';
  }
}

/**
 * Singleton instance
 */
export const agentRegistry = new AgentRegistry();
