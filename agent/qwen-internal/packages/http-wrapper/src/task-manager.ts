/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import type {
  TaskState,
  TaskStatus,
  WrapperConfig,
  WrapperSSEEvent,
  StatusEvent,
} from './types.js';
import { broadcastSSEEvent, closeSSE } from './utils/sse.js';

/**
 * Manages concurrent task executions
 */
export class TaskManager {
  private tasks: Map<string, TaskState> = new Map();
  private cleanupInterval: NodeJS.Timeout;
  private readonly CLEANUP_INTERVAL_MS = 60000; // 1 minute
  private readonly COMPLETED_TASK_TTL_MS = 3600000; // 1 hour

  constructor() {
    // Periodically clean up old completed tasks
    this.cleanupInterval = setInterval(() => {
      this.cleanupCompletedTasks();
    }, this.CLEANUP_INTERVAL_MS);
  }

  /**
   * Create a new task
   */
  createTask(task: string, config: WrapperConfig = {}): string {
    const taskId = uuidv4();
    const now = Date.now();

    const taskState: TaskState = {
      taskId,
      status: 'pending',
      config,
      task,
      createdAt: now,
      abortController: new AbortController(),
      sseConnections: new Set(),
      events: [],
    };

    this.tasks.set(taskId, taskState);
    return taskId;
  }

  /**
   * Get task by ID
   */
  getTask(taskId: string): TaskState | undefined {
    return this.tasks.get(taskId);
  }

  /**
   * Update task status
   */
  updateTaskStatus(taskId: string, status: TaskStatus, message?: string): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      return;
    }

    task.status = status;

    if (status === 'running' && !task.startedAt) {
      task.startedAt = Date.now();
    } else if (
      (status === 'completed' || status === 'error' || status === 'cancelled') &&
      !task.completedAt
    ) {
      task.completedAt = Date.now();
    }

    // Broadcast status update
    const statusEvent: StatusEvent = {
      type: 'status',
      timestamp: Date.now(),
      taskId,
      status,
      message,
    };

    this.broadcastEvent(taskId, statusEvent);
  }

  /**
   * Set task result
   */
  setTaskResult(taskId: string, result: string): void {
    const task = this.tasks.get(taskId);
    if (task) {
      task.result = result;
    }
  }

  /**
   * Set task error
   */
  setTaskError(taskId: string, error: string): void {
    const task = this.tasks.get(taskId);
    if (task) {
      task.error = error;
      this.updateTaskStatus(taskId, 'error');
    }
  }

  /**
   * Add SSE connection for a task
   */
  addSSEConnection(taskId: string, res: Response): boolean {
    const task = this.tasks.get(taskId);
    if (!task) {
      return false;
    }

    task.sseConnections.add(res);

    // Remove connection when client disconnects
    res.on('close', () => {
      task.sseConnections.delete(res);
    });

    return true;
  }

  /**
   * Broadcast event to all SSE connections for a task
   */
  broadcastEvent(taskId: string, event: WrapperSSEEvent): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      return;
    }

    // Store event in history
    task.events.push(event);

    // Broadcast to all connected clients
    broadcastSSEEvent(task.sseConnections, event);
  }

  /**
   * Cancel a task
   */
  cancelTask(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    if (!task) {
      return false;
    }

    if (
      task.status === 'completed' ||
      task.status === 'error' ||
      task.status === 'cancelled'
    ) {
      return false; // Already finished
    }

    // Abort the task
    task.abortController.abort();
    this.updateTaskStatus(taskId, 'cancelled', 'Task cancelled by user');

    // Close all SSE connections
    task.sseConnections.forEach((res) => closeSSE(res));
    task.sseConnections.clear();

    return true;
  }

  /**
   * Set pending question for a task
   */
  setPendingQuestion(
    taskId: string,
    questionId: string,
    question: string,
    context: string | undefined,
    resolve: (answer: string) => void,
  ): void {
    const task = this.tasks.get(taskId);
    if (!task) {
      return;
    }

    task.pendingQuestion = {
      questionId,
      question,
      context,
      resolve,
    };

    this.updateTaskStatus(taskId, 'waiting_for_answer');
  }

  /**
   * Answer a pending question
   */
  answerQuestion(taskId: string, answer: string): boolean {
    const task = this.tasks.get(taskId);
    if (!task || !task.pendingQuestion) {
      return false;
    }

    // Resolve the promise with the answer
    task.pendingQuestion.resolve(answer);
    task.pendingQuestion = undefined;

    // Update status back to running
    this.updateTaskStatus(taskId, 'running', 'Question answered, resuming task');

    return true;
  }

  /**
   * Check if task has pending question
   */
  hasPendingQuestion(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    return task?.pendingQuestion !== undefined;
  }

  /**
   * Get all tasks
   */
  getAllTasks(): TaskState[] {
    return Array.from(this.tasks.values());
  }

  /**
   * Get active tasks (not completed, error, or cancelled)
   */
  getActiveTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter(
      (task) =>
        task.status !== 'completed' &&
        task.status !== 'error' &&
        task.status !== 'cancelled',
    );
  }

  /**
   * Clean up old completed tasks
   */
  private cleanupCompletedTasks(): void {
    const now = Date.now();
    const tasksToDelete: string[] = [];

    this.tasks.forEach((task) => {
      const isCompleted =
        task.status === 'completed' ||
        task.status === 'error' ||
        task.status === 'cancelled';

      if (
        isCompleted &&
        task.completedAt &&
        now - task.completedAt > this.COMPLETED_TASK_TTL_MS
      ) {
        // Close any remaining SSE connections
        task.sseConnections.forEach((res) => closeSSE(res));
        task.sseConnections.clear();

        tasksToDelete.push(task.taskId);
      }
    });

    tasksToDelete.forEach((taskId) => this.tasks.delete(taskId));

    if (tasksToDelete.length > 0) {
      console.log(`Cleaned up ${tasksToDelete.length} old tasks`);
    }
  }

  /**
   * Shutdown and cleanup
   */
  shutdown(): void {
    clearInterval(this.cleanupInterval);

    // Cancel all active tasks
    this.tasks.forEach((task) => {
      if (
        task.status !== 'completed' &&
        task.status !== 'error' &&
        task.status !== 'cancelled'
      ) {
        this.cancelTask(task.taskId);
      }
    });

    this.tasks.clear();
  }
}

/**
 * Singleton instance
 */
export const taskManager = new TaskManager();

