export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  tools_used?: string[];
  duration_ms?: number;
}

export interface ChatApiResponse {
  response: string;
  intent: string;
  tools_used: string[];
  metadata: Record<string, unknown>;
}

export interface AgentStatus {
  name: string;
  url: string;
  healthy: boolean;
}
