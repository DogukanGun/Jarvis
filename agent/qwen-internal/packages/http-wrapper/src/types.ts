/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Response } from 'express';

/**
 * Task configuration options
 */
export interface WrapperConfig {
  model?: string;
  maxTurns?: number;
  approvalMode?: 'auto' | 'manual';
  allowedTools?: string[];
  workingDirectory?: string;
  timeout?: number; // minutes
  apiKey?: string;
  baseUrl?: string; // For Ollama or custom OpenAI-compatible endpoints
}

/**
 * Task execution status
 */
export type TaskStatus =
  | 'pending'
  | 'running'
  | 'waiting_for_answer'
  | 'completed'
  | 'error'
  | 'cancelled';

/**
 * SSE event types
 */
export type SSEEventType =
  | 'thought'
  | 'content'
  | 'tool_call'
  | 'tool_result'
  | 'question'
  | 'completed'
  | 'error'
  | 'status';

/**
 * Base SSE event structure
 */
export interface SSEEvent {
  type: SSEEventType;
  timestamp: number;
  taskId: string;
}

/**
 * Thought event - AI's reasoning process
 */
export interface ThoughtEvent extends SSEEvent {
  type: 'thought';
  content: string;
}

/**
 * Content event - AI's text response
 */
export interface ContentEvent extends SSEEvent {
  type: 'content';
  text: string;
}

/**
 * Tool call event - AI requesting tool execution
 */
export interface ToolCallEvent extends SSEEvent {
  type: 'tool_call';
  callId: string;
  name: string;
  args: Record<string, unknown>;
}

/**
 * Tool result event - Result of tool execution
 */
export interface ToolResultEvent extends SSEEvent {
  type: 'tool_result';
  callId: string;
  result: unknown;
  success: boolean;
}

/**
 * Question event - AI asking for user input
 */
export interface QuestionEvent extends SSEEvent {
  type: 'question';
  question: string;
  context?: string;
  questionId: string;
}

/**
 * Completed event - Task finished successfully
 */
export interface CompletedEvent extends SSEEvent {
  type: 'completed';
  result: string;
  finalText?: string;
}

/**
 * Error event - Task encountered an error
 */
export interface ErrorEvent extends SSEEvent {
  type: 'error';
  error: string;
  reason?: string;
}

/**
 * Status event - Current task status update
 */
export interface StatusEvent extends SSEEvent {
  type: 'status';
  status: TaskStatus;
  message?: string;
}

/**
 * Union of all SSE events
 */
export type WrapperSSEEvent =
  | ThoughtEvent
  | ContentEvent
  | ToolCallEvent
  | ToolResultEvent
  | QuestionEvent
  | CompletedEvent
  | ErrorEvent
  | StatusEvent;

/**
 * Task state
 */
export interface TaskState {
  taskId: string;
  status: TaskStatus;
  config: WrapperConfig;
  task: string;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  result?: string;
  error?: string;
  abortController: AbortController;
  sseConnections: Set<Response>;
  pendingQuestion?: {
    questionId: string;
    question: string;
    context?: string;
    resolve: (answer: string) => void;
  };
  events: WrapperSSEEvent[];
}

/**
 * Request body for starting a task
 */
export interface StartTaskRequest {
  task: string;
  config?: WrapperConfig;
}

/**
 * Response for starting a task
 */
export interface StartTaskResponse {
  taskId: string;
  streamUrl: string;
  status: TaskStatus;
}

/**
 * Request body for answering a question
 */
export interface AnswerQuestionRequest {
  answer: string;
}

/**
 * Response for answering a question
 */
export interface AnswerQuestionResponse {
  success: boolean;
  message: string;
}

/**
 * Response for task status
 */
export interface TaskStatusResponse {
  taskId: string;
  status: TaskStatus;
  task: string;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  result?: string;
  error?: string;
  hasPendingQuestion: boolean;
  pendingQuestion?: {
    questionId: string;
    question: string;
    context?: string;
  };
}

/**
 * Response for canceling a task
 */
export interface CancelTaskResponse {
  success: boolean;
  message: string;
  taskId: string;
}

/**
 * Question detection result
 */
export interface QuestionDetectionResult {
  isQuestion: boolean;
  question?: string;
  context?: string;
  confidence: 'high' | 'medium' | 'low';
  detectionMethod: 'explicit_tool' | 'question_mark' | 'next_speaker_check' | 'none';
}

