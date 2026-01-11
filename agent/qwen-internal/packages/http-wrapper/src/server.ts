/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import type {
  StartTaskRequest,
  StartTaskResponse,
  AnswerQuestionRequest,
  AnswerQuestionResponse,
  TaskStatusResponse,
  CancelTaskResponse,
} from './types.js';
import { taskManager } from './task-manager.js';
import { wrapperService } from './wrapper.js';
import { setupSSE, setupSSEKeepalive } from './utils/sse.js';

/**
 * HTTP server with REST API and SSE for Qwen Code wrapper
 */
export default class WrapperServer {
  private app: express.Application;
  private port: number;
  private server?: ReturnType<typeof this.app.listen>;

  constructor(port: number = 3000) {
    this.port = port;
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  /**
   * Setup Express middleware
   */
  private setupMiddleware(): void {
    this.app.use(cors());
    this.app.use(express.json());

    // Request logging
    this.app.use((req, _res, next) => {
      console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
      next();
    });
  }

  /**
   * Setup API routes
   */
  private setupRoutes(): void {
    // Health check
    this.app.get('/health', (_req, res) => {
      res.json({
        status: 'ok',
        timestamp: Date.now(),
        activeTasks: taskManager.getActiveTasks().length,
      });
    });

    // Start a new task
    this.app.post('/api/task/start', (req, res) => {
      this.handleStartTask(req, res);
    });

    // Get task status
    this.app.get('/api/task/:taskId/status', (req, res) => {
      this.handleGetTaskStatus(req, res);
    });

    // Stream task events (SSE)
    this.app.get('/api/task/:taskId/stream', (req, res) => {
      this.handleStreamTask(req, res);
    });

    // Answer a pending question
    this.app.post('/api/task/:taskId/answer', (req, res) => {
      this.handleAnswerQuestion(req, res);
    });

    // Cancel a task
    this.app.post('/api/task/:taskId/cancel', (req, res) => {
      this.handleCancelTask(req, res);
    });

    // List all tasks
    this.app.get('/api/tasks', (_req, res) => {
      const tasks = taskManager.getAllTasks().map((task) => ({
        taskId: task.taskId,
        status: task.status,
        task: task.task,
        createdAt: task.createdAt,
        startedAt: task.startedAt,
        completedAt: task.completedAt,
        hasPendingQuestion: !!task.pendingQuestion,
      }));

      res.json({ tasks });
    });
  }

  /**
   * Handle POST /api/task/start
   */
  private handleStartTask(req: Request, res: Response): void {
    try {
      const body = req.body as StartTaskRequest;

      if (!body.task) {
        res.status(400).json({ error: 'Missing required field: task' });
        return;
      }

      // Create task
      const taskId = taskManager.createTask(body.task, body.config || {});

      // Start task execution asynchronously
      wrapperService
        .executeTask(taskId, body.task, body.config || {})
        .catch((error) => {
          console.error(`Task ${taskId} execution error:`, error);
        });

      const response: StartTaskResponse = {
        taskId,
        streamUrl: `/api/task/${taskId}/stream`,
        status: 'pending',
      };

      res.status(201).json(response);
    } catch (error) {
      console.error('Error starting task:', error);
      res.status(500).json({
        error: 'Failed to start task',
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Handle GET /api/task/:taskId/status
   */
  private handleGetTaskStatus(req: Request, res: Response): void {
    const { taskId } = req.params;
    const task = taskManager.getTask(taskId);

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const response: TaskStatusResponse = {
      taskId: task.taskId,
      status: task.status,
      task: task.task,
      createdAt: task.createdAt,
      startedAt: task.startedAt,
      completedAt: task.completedAt,
      result: task.result,
      error: task.error,
      hasPendingQuestion: !!task.pendingQuestion,
      pendingQuestion: task.pendingQuestion
        ? {
            questionId: task.pendingQuestion.questionId,
            question: task.pendingQuestion.question,
            context: task.pendingQuestion.context,
          }
        : undefined,
    };

    res.json(response);
  }

  /**
   * Handle GET /api/task/:taskId/stream (SSE)
   */
  private handleStreamTask(req: Request, res: Response): void {
    const { taskId } = req.params;
    const task = taskManager.getTask(taskId);

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Setup SSE
    setupSSE(res);

    // Add connection to task
    const added = taskManager.addSSEConnection(taskId, res);
    if (!added) {
      res.end();
      return;
    }

    // Setup keepalive
    const keepaliveInterval = setupSSEKeepalive(res);

    // Send historical events
    task.events.forEach((event) => {
      res.write(`event: ${event.type}\n`);
      res.write(`data: ${JSON.stringify(event)}\n\n`);
    });

    // Handle client disconnect
    req.on('close', () => {
      clearInterval(keepaliveInterval);
      task.sseConnections.delete(res);
    });
  }

  /**
   * Handle POST /api/task/:taskId/answer
   */
  private handleAnswerQuestion(req: Request, res: Response): void {
    const { taskId } = req.params;
    const body = req.body as AnswerQuestionRequest;

    if (!body.answer) {
      res.status(400).json({ error: 'Missing required field: answer' });
      return;
    }

    const success = taskManager.answerQuestion(taskId, body.answer);

    if (!success) {
      res.status(404).json({
        error: 'No pending question found for this task',
      });
      return;
    }

    const response: AnswerQuestionResponse = {
      success: true,
      message: 'Answer submitted successfully',
    };

    res.json(response);
  }

  /**
   * Handle POST /api/task/:taskId/cancel
   */
  private handleCancelTask(req: Request, res: Response): void {
    const { taskId } = req.params;
    const success = taskManager.cancelTask(taskId);

    if (!success) {
      res.status(404).json({
        error: 'Task not found or already completed',
      });
      return;
    }

    const response: CancelTaskResponse = {
      success: true,
      message: 'Task cancelled successfully',
      taskId,
    };

    res.json(response);
  }

  /**
   * Start the server
   */
  start(): Promise<void> {
    return new Promise((resolve) => {
      this.server = this.app.listen(this.port, () => {
        console.log(`Qwen Code HTTP Wrapper listening on port ${this.port}`);
        console.log(`Health check: http://localhost:${this.port}/health`);
        console.log(`API base URL: http://localhost:${this.port}/api`);
        resolve();
      });
    });
  }

  /**
   * Stop the server
   */
  async stop(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.server) {
        resolve();
        return;
      }

      // Shutdown task manager
      taskManager.shutdown();

      this.server.close((err) => {
        if (err) {
          reject(err);
        } else {
          console.log('Server stopped');
          resolve();
        }
      });
    });
  }

  /**
   * Get the Express app instance
   */
  getApp(): express.Application {
    return this.app;
  }
}

/**
 * Main entry point
 */
if (import.meta.url === `file://${process.argv[1]}`) {
  const port = process.env['PORT'] ? parseInt(process.env['PORT']) : 3000;
  const server = new WrapperServer(port);

  server.start().catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    await server.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('\nShutting down...');
    await server.stop();
    process.exit(0);
  });
}
