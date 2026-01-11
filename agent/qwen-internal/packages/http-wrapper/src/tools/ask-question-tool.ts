/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  BaseDeclarativeTool,
  BaseToolInvocation,
  Kind,
  type ToolResult,
} from '@qwen-code/qwen-code-core';

/**
 * Parameters for the ask_question tool
 */
export interface AskQuestionParams {
  question: string;
  context?: string;
}

/**
 * Callback type for handling questions
 */
export type QuestionHandler = (
  question: string,
  context?: string,
) => Promise<string>;

/**
 * Tool for agents to explicitly ask questions to the orchestrator/user
 */
export class AskQuestionTool extends BaseDeclarativeTool<
  AskQuestionParams,
  ToolResult
> {
  private questionHandler?: QuestionHandler;

  constructor() {
    super(
      'ask_question',
      'Ask Question',
      'Ask a question to the orchestrator/user and wait for their response. Use this when you need clarification, additional information, or a decision from the user.',
      Kind.Other,
      {
        type: 'object',
        properties: {
          question: {
            type: 'string',
            description:
              'The question to ask the user. Be clear and specific.',
          },
          context: {
            type: 'string',
            description:
              'Optional context or background information to help the user understand the question.',
          },
        },
        required: ['question'],
      },
      false, // isOutputMarkdown
      false, // canUpdateOutput
    );
  }

  /**
   * Set the question handler callback
   */
  setQuestionHandler(handler: QuestionHandler): void {
    this.questionHandler = handler;
  }

  protected createInvocation(params: AskQuestionParams): AskQuestionToolInvocation {
    if (!this.questionHandler) {
      throw new Error('Question handler not set');
    }
    return new AskQuestionToolInvocation(params, this.questionHandler);
  }
}

/**
 * Tool invocation for ask_question
 */
class AskQuestionToolInvocation extends BaseToolInvocation<
  AskQuestionParams,
  ToolResult
> {
  constructor(
    params: AskQuestionParams,
    private questionHandler: QuestionHandler,
  ) {
    super(params);
  }

  getDescription(): string {
    return `Asking question: "${this.params.question}"${
      this.params.context ? `\nContext: ${this.params.context}` : ''
    }`;
  }

  override async shouldConfirmExecute(): Promise<false> {
    // No confirmation needed, this tool is inherently interactive
    return false;
  }

  async execute(_signal?: AbortSignal): Promise<ToolResult> {
    try {
      // Call the question handler and wait for the answer
      const answer = await this.questionHandler(
        this.params.question,
        this.params.context,
      );

      return {
        llmContent: `User's answer: ${answer}`,
        returnDisplay: answer,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      return {
        llmContent: `Error asking question: ${errorMessage}`,
        returnDisplay: errorMessage,
      };
    }
  }
}

