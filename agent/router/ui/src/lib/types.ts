export interface Finding {
  type: string;
  severity: string;
  description: string;
  details?: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  intent?: string;
  tools_used?: string[];
  findings?: Finding[];
  report?: Record<string, unknown>;
  duration_ms?: number;
}

export interface ChatApiResponse {
  response: string;
  intent: string;
  tools_used: string[];
  findings: Finding[];
  report: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface AgentStatus {
  name: string;
  url: string;
  healthy: boolean;
}
