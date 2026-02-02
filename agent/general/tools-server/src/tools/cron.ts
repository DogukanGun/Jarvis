import { Type } from "@sinclair/typebox";
import type { Tool, ToolResult } from "../shared/common.js";
import { jsonResult, readStringParam } from "../shared/common.js";

// Simple in-memory cron job storage
type CronJob = {
  id: string;
  name: string;
  schedule: string;
  command: string;
  enabled: boolean;
  lastRun: string | null;
  nextRun: string | null;
  runCount: number;
  createdAt: string;
};

const cronJobs = new Map<string, CronJob>();
const cronTimers = new Map<string, NodeJS.Timeout>();
let jobIdCounter = 0;

function generateJobId(): string {
  return `job_${++jobIdCounter}`;
}

// Parse cron expression to get next run time (simplified)
function parseNextRun(schedule: string): Date | null {
  const now = new Date();
  const parts = schedule.split(" ");

  if (parts.length < 5) return null;

  try {
    // Very simplified cron parsing - handles common patterns
    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

    const next = new Date(now);
    next.setSeconds(0);
    next.setMilliseconds(0);

    // Handle specific minute
    if (minute !== "*") {
      const targetMinute = parseInt(minute, 10);
      if (next.getMinutes() >= targetMinute) {
        next.setHours(next.getHours() + 1);
      }
      next.setMinutes(targetMinute);
    } else {
      next.setMinutes(next.getMinutes() + 1);
    }

    // Handle specific hour
    if (hour !== "*") {
      const targetHour = parseInt(hour, 10);
      if (next.getHours() > targetHour || (next.getHours() === targetHour && minute === "*")) {
        next.setDate(next.getDate() + 1);
      }
      next.setHours(targetHour);
    }

    return next;
  } catch {
    return null;
  }
}

// Calculate interval in ms from cron expression (simplified)
function getIntervalMs(schedule: string): number {
  const parts = schedule.split(" ");
  if (parts.length < 5) return 60000; // Default to 1 minute

  const [minute, hour] = parts;

  // Every minute: * * * * *
  if (minute === "*" && hour === "*") {
    return 60 * 1000;
  }

  // Every hour at specific minute: X * * * *
  if (minute !== "*" && hour === "*") {
    return 60 * 60 * 1000;
  }

  // Daily at specific time: X X * * *
  if (minute !== "*" && hour !== "*") {
    return 24 * 60 * 60 * 1000;
  }

  // Default to hourly
  return 60 * 60 * 1000;
}

async function executeJob(job: CronJob): Promise<void> {
  console.log(`[Cron] Executing job ${job.id}: ${job.name}`);

  try {
    // Execute the command using the exec tool's logic
    const { exec } = await import("node:child_process");
    const { promisify } = await import("node:util");
    const execAsync = promisify(exec);

    const { stdout, stderr } = await execAsync(job.command, {
      timeout: 60000,
      maxBuffer: 10 * 1024 * 1024,
    });

    console.log(`[Cron] Job ${job.id} completed. stdout: ${stdout.slice(0, 200)}`);
    if (stderr) {
      console.log(`[Cron] Job ${job.id} stderr: ${stderr.slice(0, 200)}`);
    }
  } catch (error) {
    console.error(`[Cron] Job ${job.id} failed:`, error);
  }

  // Update job state
  job.lastRun = new Date().toISOString();
  job.runCount++;
  job.nextRun = parseNextRun(job.schedule)?.toISOString() || null;
}

function scheduleJob(job: CronJob): void {
  // Clear existing timer if any
  const existingTimer = cronTimers.get(job.id);
  if (existingTimer) {
    clearInterval(existingTimer);
  }

  if (!job.enabled) return;

  const intervalMs = getIntervalMs(job.schedule);
  const nextRun = parseNextRun(job.schedule);

  if (nextRun) {
    job.nextRun = nextRun.toISOString();

    // Set up the first run
    const delayMs = Math.max(0, nextRun.getTime() - Date.now());

    setTimeout(() => {
      executeJob(job);

      // Set up recurring runs
      const timer = setInterval(() => {
        if (job.enabled) {
          executeJob(job);
        }
      }, intervalMs);

      cronTimers.set(job.id, timer);
    }, delayMs);
  }
}

const CronSchema = Type.Object({
  action: Type.String({
    description: 'Cron action: "status", "list", "add", "update", "remove", "run"',
  }),
  id: Type.Optional(Type.String({ description: "Job ID for update/remove/run" })),
  name: Type.Optional(Type.String({ description: "Job name (for add)" })),
  schedule: Type.Optional(
    Type.String({ description: 'Cron schedule expression, e.g. "*/5 * * * *" for every 5 mins' })
  ),
  command: Type.Optional(Type.String({ description: "Shell command to execute" })),
  enabled: Type.Optional(Type.Boolean({ description: "Whether job is enabled" })),
});

async function handleCronAction(params: Record<string, unknown>): Promise<unknown> {
  const action = readStringParam(params, "action", { required: true });

  switch (action) {
    case "status": {
      return {
        running: true,
        jobCount: cronJobs.size,
        enabledCount: Array.from(cronJobs.values()).filter((j) => j.enabled).length,
      };
    }

    case "list": {
      const jobs = Array.from(cronJobs.values()).map((job) => ({
        id: job.id,
        name: job.name,
        schedule: job.schedule,
        command: job.command.slice(0, 100) + (job.command.length > 100 ? "..." : ""),
        enabled: job.enabled,
        lastRun: job.lastRun,
        nextRun: job.nextRun,
        runCount: job.runCount,
      }));
      return { jobs };
    }

    case "add": {
      const name = readStringParam(params, "name", { required: true });
      const schedule = readStringParam(params, "schedule", { required: true });
      const command = readStringParam(params, "command", { required: true });
      const enabled = params.enabled !== false;

      const id = generateJobId();
      const job: CronJob = {
        id,
        name,
        schedule,
        command,
        enabled,
        lastRun: null,
        nextRun: null,
        runCount: 0,
        createdAt: new Date().toISOString(),
      };

      cronJobs.set(id, job);
      scheduleJob(job);

      return {
        created: true,
        job: {
          id: job.id,
          name: job.name,
          schedule: job.schedule,
          enabled: job.enabled,
          nextRun: job.nextRun,
        },
      };
    }

    case "update": {
      const id = readStringParam(params, "id", { required: true });
      const job = cronJobs.get(id);
      if (!job) throw new Error(`Job not found: ${id}`);

      const name = readStringParam(params, "name");
      const schedule = readStringParam(params, "schedule");
      const command = readStringParam(params, "command");
      const enabled = params.enabled;

      if (name) job.name = name;
      if (schedule) job.schedule = schedule;
      if (command) job.command = command;
      if (typeof enabled === "boolean") job.enabled = enabled;

      // Reschedule if schedule or enabled changed
      scheduleJob(job);

      return {
        updated: true,
        job: {
          id: job.id,
          name: job.name,
          schedule: job.schedule,
          enabled: job.enabled,
          nextRun: job.nextRun,
        },
      };
    }

    case "remove": {
      const id = readStringParam(params, "id", { required: true });
      const job = cronJobs.get(id);
      if (!job) throw new Error(`Job not found: ${id}`);

      // Clear timer
      const timer = cronTimers.get(id);
      if (timer) {
        clearInterval(timer);
        cronTimers.delete(id);
      }

      cronJobs.delete(id);

      return { removed: true, id };
    }

    case "run": {
      const id = readStringParam(params, "id", { required: true });
      const job = cronJobs.get(id);
      if (!job) throw new Error(`Job not found: ${id}`);

      await executeJob(job);

      return {
        executed: true,
        job: {
          id: job.id,
          name: job.name,
          lastRun: job.lastRun,
          runCount: job.runCount,
        },
      };
    }

    default:
      throw new Error(`Unknown cron action: ${action}`);
  }
}

export function createCronTool(): Tool {
  return {
    label: "Cron",
    name: "cron",
    description: `Manage scheduled tasks (cron jobs). Actions:
- status: Get cron system status
- list: List all scheduled jobs
- add: Create a new cron job (name, schedule, command required)
- update: Update an existing job by ID
- remove: Delete a job by ID
- run: Manually execute a job immediately

Schedule format: standard cron (minute hour day month weekday)
Examples: "*/5 * * * *" (every 5 mins), "0 9 * * *" (daily at 9am)`,
    parameters: CronSchema,
    execute: async (args): Promise<ToolResult> => {
      const params = args as Record<string, unknown>;
      const result = await handleCronAction(params);
      return jsonResult(result);
    },
  };
}
