export type ToolCategory = 'wifi' | 'network' | 'exploitation' | 'post_exploitation' | 'password' | 'monitoring' | 'ctf';

export type AuthLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ToolParameter {
  name: string;
  type: string;
  required: boolean;
  default?: unknown;
  description: string;
  choices?: string[];
}

export interface ToolMetadata {
  name: string;
  display_name: string;
  category: ToolCategory;
  description: string;
  capabilities: string[];
  auth_level: AuthLevel;
  parameters: ToolParameter[];
  binary_path?: string;
  is_long_running?: boolean;
  estimated_duration?: string;
}

export interface ExecuteRequest {
  user_id: string;
  message: string;
  target_tools?: string[];
  parameters?: Record<string, unknown>;
}

export interface ExecuteResponse {
  response: string;
  report: Record<string, unknown>;
  tools_used: string[];
  findings: Finding[];
  job_ids: string[];
  requires_confirmation: boolean;
  confirmation_prompt: string;
  job_id?: string;
}

export interface AsyncExecuteResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'waiting_confirmation' | 'running' | 'completed' | 'failed' | 'confirmed';
  tool_name: string;
  started_at: string;
  result?: Record<string, unknown>;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface Finding {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description: string;
  tool?: string;
  details?: Record<string, unknown>;
}

export interface ToolEvent {
  timestamp: string;
  type: string;
  job_id?: string;
  tool_name?: string;
  data?: unknown;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  response?: ExecuteResponse;
  isLoading?: boolean;
}

export type MainTab = 'dashboard' | 'tool-detail' | 'chat' | 'jobs' | 'results';
