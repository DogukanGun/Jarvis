/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Turn } from '@qwen-code/qwen-code-core';
import type { QuestionDetectionResult } from './types.js';

/**
 * Detects when the agent is asking a question using multiple methods
 */
export class QuestionDetector {
  /**
   * Detect if there's an explicit ask_question tool call
   */
  detectExplicitQuestion(turn: Turn): QuestionDetectionResult {
    const askQuestionCalls = turn.pendingToolCalls.filter(
      (call) => call.name === 'ask_question',
    );

    if (askQuestionCalls.length > 0) {
      const firstCall = askQuestionCalls[0];
      const args = firstCall.args as {
        question: string;
        context?: string;
      };

      return {
        isQuestion: true,
        question: args.question,
        context: args.context,
        confidence: 'high',
        detectionMethod: 'explicit_tool',
      };
    }

    return {
      isQuestion: false,
      confidence: 'high',
      detectionMethod: 'none',
    };
  }

  /**
   * Detect implicit questions from text patterns
   */
  detectImplicitQuestion(
    content: string,
    hasPendingToolCalls: boolean,
  ): QuestionDetectionResult {
    if (hasPendingToolCalls) {
      // Don't detect implicit questions if there are pending tool calls
      return {
        isQuestion: false,
        confidence: 'high',
        detectionMethod: 'none',
      };
    }

    const trimmedContent = content.trim();

    // Check if ends with question mark
    if (trimmedContent.endsWith('?')) {
      // Extract the last sentence as the question
      const sentences = trimmedContent.split(/[.!?]+/).filter(s => s.trim());
      const lastSentence = sentences[sentences.length - 1]?.trim() + '?';

      return {
        isQuestion: true,
        question: lastSentence,
        context: sentences.length > 1 ? sentences.slice(0, -1).join('. ') : undefined,
        confidence: 'medium',
        detectionMethod: 'question_mark',
      };
    }

    // Check for common question patterns
    const questionPatterns = [
      /(?:should I|shall I|would you like me to|do you want me to|can I|may I)\s+.+\?$/i,
      /(?:which|what|how|where|when|why|who)\s+.+\?$/i,
      /please (?:let me know|tell me|confirm|clarify)/i,
      /(?:need|require) (?:your|user) (?:input|decision|clarification|confirmation)/i,
      /waiting for (?:your|user) (?:response|answer|decision|input)/i,
    ];

    for (const pattern of questionPatterns) {
      if (pattern.test(trimmedContent)) {
        return {
          isQuestion: true,
          question: trimmedContent,
          confidence: 'low',
          detectionMethod: 'question_mark',
        };
      }
    }

    return {
      isQuestion: false,
      confidence: 'high',
      detectionMethod: 'none',
    };
  }

  /**
   * Detect questions from turn completion
   */
  detectFromTurnCompletion(
    turn: Turn,
    contentBuffer: string,
  ): QuestionDetectionResult {
    // First check for explicit ask_question tool call
    const explicitResult = this.detectExplicitQuestion(turn);
    if (explicitResult.isQuestion) {
      return explicitResult;
    }

    // If no pending tool calls, check implicit patterns
    if (turn.pendingToolCalls.length === 0) {
      return this.detectImplicitQuestion(contentBuffer, false);
    }

    return {
      isQuestion: false,
      confidence: 'high',
      detectionMethod: 'none',
    };
  }

  /**
   * Main detection method that combines all strategies
   */
  detect(turn: Turn, contentBuffer: string): QuestionDetectionResult {
    return this.detectFromTurnCompletion(turn, contentBuffer);
  }
}

