/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  AuthType,
  Config,
  GeminiClient,
} from '@qwen-code/qwen-code-core';
import { v4 as uuidv4 } from 'uuid';
import type {
  WrapperConfig,
  QuestionEvent,
  CompletedEvent,
  ErrorEvent,
} from './types.js';
import { EventMonitor } from './event-monitor.js';
import { QuestionDetector } from './question-detector.js';
import { AskQuestionTool } from './tools/ask-question-tool.js';
import { taskManager } from './task-manager.js';

/**
 * Wrapper service that integrates Qwen Code's @core module
 * with the multi-agent orchestrator system
 */
export class WrapperService {
  private askQuestionTool: AskQuestionTool;

  constructor() {
    this.askQuestionTool = new AskQuestionTool();
  }

  /**
   * Execute a task with the Qwen Code core module
   */
  async executeTask(taskId: string, task: string, config: WrapperConfig): Promise<void> {
    const taskState = taskManager.getTask(taskId);
    if (!taskState) {
      throw new Error(`Task ${taskId} not found`);
    }

    try {
      // Update status to running
      taskManager.updateTaskStatus(taskId, 'running', 'Task execution started');

      // Create Config instance for the core module
      const coreConfig = await this.createCoreConfig(taskId, config);
      
      // Initialize the config (this creates toolRegistry, etc.)
      await coreConfig.initialize();

      // Set up ask_question tool handler
      this.setupAskQuestionHandler(taskId);

      // Register the ask_question tool
      const toolRegistry = coreConfig.getToolRegistry();
      toolRegistry.registerTool(this.askQuestionTool);

      // Initialize GeminiClient
      const client = new GeminiClient(coreConfig);
      await client.initialize();

      // Create event monitor and question detector
      const eventMonitor = new EventMonitor(taskId);
      const questionDetector = new QuestionDetector();

      // Execute the task
      const result = await this.runTask(
        client,
        task,
        taskId,
        taskState.abortController.signal,
        eventMonitor,
        questionDetector,
      );

      // Set result and mark as completed
      taskManager.setTaskResult(taskId, result);
      
      const completedEvent: CompletedEvent = {
        type: 'completed',
        timestamp: Date.now(),
        taskId,
        result,
        finalText: eventMonitor.getContentBuffer(),
      };
      
      taskManager.broadcastEvent(taskId, completedEvent);
      taskManager.updateTaskStatus(taskId, 'completed', 'Task completed successfully');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Check if it's a cancellation
      if (taskState.abortController.signal.aborted) {
        taskManager.updateTaskStatus(taskId, 'cancelled', 'Task was cancelled');
      } else {
        taskManager.setTaskError(taskId, errorMessage);
        
        const errorEvent: ErrorEvent = {
          type: 'error',
          timestamp: Date.now(),
          taskId,
          error: errorMessage,
        };
        
        taskManager.broadcastEvent(taskId, errorEvent);
      }
      
      throw error;
    }
  }

  /**
   * Run the task and process events
   */
  private async runTask(
    client: GeminiClient,
    task: string,
    taskId: string,
    signal: AbortSignal,
    eventMonitor: EventMonitor,
    questionDetector: QuestionDetector,
  ): Promise<string> {
    const promptId = `${taskId}-${Date.now()}`;
    const requestParts = [{ text: task }];

    // Stream events from the core module using manual iteration
    const stream = client.sendMessageStream(requestParts, signal, promptId);
    
    let turn;
    let result = await stream.next();
    
    while (!result.done) {
      const event = result.value;
      
      // Check if task was cancelled
      if (signal.aborted) {
        break;
      }

      // Transform and broadcast core events
      const wrapperEvent = eventMonitor.transformEvent(event);
      if (wrapperEvent) {
        taskManager.broadcastEvent(taskId, wrapperEvent);
      }
      
      result = await stream.next();
    }
    
    // When done, result.value contains the Turn
    turn = result.value as any;

    // Check if there's a pending question
    if (turn && 'pendingToolCalls' in turn) {
      const questionResult = questionDetector.detect(turn, eventMonitor.getContentBuffer());
      
      if (questionResult.isQuestion && questionResult.question) {
        // Wait for answer
        const answer = await this.waitForAnswer(
          taskId,
          questionResult.question,
          questionResult.context,
        );

        // Continue execution with the answer
        const continuePromptId = `${taskId}-continue-${Date.now()}`;
        const continueParts = [{ text: answer }];
        
        const continueStream = client.sendMessageStream(
          continueParts,
          signal,
          continuePromptId,
        );

        let continueResult = await continueStream.next();
        
        while (!continueResult.done) {
          if (signal.aborted) break;
          
          const event = continueResult.value;
          const wrapperEvent = eventMonitor.transformEvent(event);
          if (wrapperEvent) {
            taskManager.broadcastEvent(taskId, wrapperEvent);
          }
          
          continueResult = await continueStream.next();
        }
      }
    }

    // Return the accumulated content as result
    return eventMonitor.getContentBuffer() || 'Task completed';
  }

  /**
   * Wait for an answer to a question
   */
  private async waitForAnswer(
    taskId: string,
    question: string,
    context?: string,
  ): Promise<string> {
    return new Promise<string>((resolve) => {
      const questionId = uuidv4();

      // Send question event
      const questionEvent: QuestionEvent = {
        type: 'question',
        timestamp: Date.now(),
        taskId,
        question,
        context,
        questionId,
      };

      taskManager.broadcastEvent(taskId, questionEvent);
      taskManager.setPendingQuestion(taskId, questionId, question, context, resolve);
    });
  }

  /**
   * Setup the ask_question tool handler
   */
  private setupAskQuestionHandler(taskId: string): void {
    this.askQuestionTool.setQuestionHandler(async (question, context) => {
      return this.waitForAnswer(taskId, question, context);
    });
  }

  /**
   * Create a Config instance for the core module
   */
  private async createCoreConfig(taskId: string, wrapperConfig: WrapperConfig): Promise<Config> {
    const workingDir = wrapperConfig?.workingDirectory || process.cwd();
    
    // Default to Ollama setup
    const ollamaBaseUrl =  'http://localhost:11434/v1';
    const defaultModel =  'gpt-oss:20b';
    const apiKey =  'ollama'; // Ollama doesn't need a real key
    const baseUrl = wrapperConfig?.baseUrl || ollamaBaseUrl;
    
    const configOptions: any = {
      targetDir: workingDir,
      cwd: workingDir,
      sessionId: taskId,
      model: wrapperConfig?.model || defaultModel,
      maxTurns: wrapperConfig?.maxTurns || 50,
      approvalMode: wrapperConfig?.approvalMode || 'auto',
      authType: 'openai', // Critical: Use OpenAI-compatible mode for Ollama
      debugMode: false,
      generationConfig: {
        model: wrapperConfig?.model || defaultModel,
        baseUrl: baseUrl,
        apiKey: apiKey,
        authType: 'apiKey',
      },
    };

    // Create config
    const config = new Config(configOptions);
    
    // Initialize the content generator by calling refreshAuth
    await config.refreshAuth(AuthType.USE_OPENAI, true);

    return config;
  }
}

/**
 * Singleton instance
 */
export const wrapperService = new WrapperService();

