import { Type } from "@sinclair/typebox";
import { exec, spawn } from "node:child_process";
import { promisify } from "node:util";
import type { Tool, ToolResult } from "../shared/common.js";
import { jsonResult, readNumberParam, readStringParam } from "../shared/common.js";

const execAsync = promisify(exec);

const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_OUTPUT_CHARS = 50_000;

const ExecSchema = Type.Object({
  command: Type.String({ description: "The shell command to execute." }),
  cwd: Type.Optional(
    Type.String({ description: "Working directory for the command." })
  ),
  timeout: Type.Optional(
    Type.Number({
      description: "Timeout in milliseconds (default: 30000).",
      minimum: 1000,
      maximum: 300000,
    })
  ),
});

function truncateOutput(output: string, maxChars: number): { text: string; truncated: boolean } {
  if (output.length <= maxChars) return { text: output, truncated: false };
  return { text: output.slice(0, maxChars) + "\n... (truncated)", truncated: true };
}

async function runCommand(params: {
  command: string;
  cwd?: string;
  timeoutMs: number;
}): Promise<{
  stdout: string;
  stderr: string;
  exitCode: number;
  tookMs: number;
  truncated: boolean;
}> {
  const start = Date.now();

  try {
    const { stdout, stderr } = await execAsync(params.command, {
      cwd: params.cwd,
      timeout: params.timeoutMs,
      maxBuffer: 10 * 1024 * 1024, // 10MB
      shell: process.platform === "win32" ? "cmd.exe" : "/bin/bash",
    });

    const stdoutResult = truncateOutput(stdout, MAX_OUTPUT_CHARS);
    const stderrResult = truncateOutput(stderr, MAX_OUTPUT_CHARS);

    return {
      stdout: stdoutResult.text,
      stderr: stderrResult.text,
      exitCode: 0,
      tookMs: Date.now() - start,
      truncated: stdoutResult.truncated || stderrResult.truncated,
    };
  } catch (error: unknown) {
    const err = error as {
      stdout?: string;
      stderr?: string;
      code?: number;
      killed?: boolean;
      signal?: string;
    };

    const stdout = err.stdout ?? "";
    const stderr = err.stderr ?? String(error);
    const exitCode = typeof err.code === "number" ? err.code : 1;

    const stdoutResult = truncateOutput(stdout, MAX_OUTPUT_CHARS);
    const stderrResult = truncateOutput(stderr, MAX_OUTPUT_CHARS);

    if (err.killed || err.signal === "SIGTERM") {
      return {
        stdout: stdoutResult.text,
        stderr: `Command timed out after ${params.timeoutMs}ms\n${stderrResult.text}`,
        exitCode: 124, // Standard timeout exit code
        tookMs: Date.now() - start,
        truncated: stdoutResult.truncated || stderrResult.truncated,
      };
    }

    return {
      stdout: stdoutResult.text,
      stderr: stderrResult.text,
      exitCode,
      tookMs: Date.now() - start,
      truncated: stdoutResult.truncated || stderrResult.truncated,
    };
  }
}

export function createExecTool(): Tool {
  return {
    label: "Shell Execute",
    name: "exec",
    description:
      "Execute a shell command and return stdout, stderr, and exit code. Use for running scripts, build commands, or system operations.",
    parameters: ExecSchema,
    execute: async (args): Promise<ToolResult> => {
      const params = args as Record<string, unknown>;
      const command = readStringParam(params, "command", { required: true });
      const cwd = readStringParam(params, "cwd");
      const timeout = readNumberParam(params, "timeout", { integer: true });

      const result = await runCommand({
        command,
        cwd,
        timeoutMs: timeout ?? DEFAULT_TIMEOUT_MS,
      });

      return jsonResult({
        command,
        cwd: cwd ?? process.cwd(),
        ...result,
      });
    },
  };
}
