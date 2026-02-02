/**
 * REST API routes for Observation Hub
 */

import { Router, type Request, type Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { agentRegistry } from '../agent-registry.js';
import type { Server as SocketServer } from 'socket.io';

const router = Router();
let prisma: PrismaClient;
let io: SocketServer;

/**
 * Initialize routes with Prisma client and Socket.IO server
 */
export function initializeRoutes(prismaClient: PrismaClient, socketServer: SocketServer): Router {
  prisma = prismaClient;
  io = socketServer;
  return router;
}

/**
 * GET /api/agents - List all connected agents
 */
router.get('/agents', async (_req: Request, res: Response) => {
  try {
    const agents = agentRegistry.getAll();
    res.json({ agents });
  } catch (error) {
    console.error('Error fetching agents:', error);
    res.status(500).json({ error: 'Failed to fetch agents' });
  }
});

/**
 * GET /api/agents/:agentId - Get specific agent info
 */
router.get('/agents/:agentId', async (req: Request, res: Response) => {
  try {
    const { agentId } = req.params;
    const agent = agentRegistry.get(agentId);

    if (!agent) {
      res.status(404).json({ error: 'Agent not found' });
      return;
    }

    // Get agent's tasks from database
    const tasks = await prisma.task.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
      take: 10,
    });

    res.json({ agent, recentTasks: tasks });
  } catch (error) {
    console.error('Error fetching agent:', error);
    res.status(500).json({ error: 'Failed to fetch agent' });
  }
});

/**
 * GET /api/tasks - List all tasks (filterable by agent, status)
 */
router.get('/tasks', async (req: Request, res: Response) => {
  try {
    const { agentId, status, limit = '50', offset = '0' } = req.query;

    const where: Record<string, unknown> = {};
    if (agentId && typeof agentId === 'string') {
      where.agentId = agentId;
    }
    if (status && typeof status === 'string') {
      where.status = status;
    }

    const tasks = await prisma.task.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      take: parseInt(limit as string, 10),
      skip: parseInt(offset as string, 10),
    });

    const total = await prisma.task.count({ where });

    res.json({ tasks, total, limit: parseInt(limit as string, 10), offset: parseInt(offset as string, 10) });
  } catch (error) {
    console.error('Error fetching tasks:', error);
    res.status(500).json({ error: 'Failed to fetch tasks' });
  }
});

/**
 * GET /api/tasks/:taskId - Get task details with events
 */
router.get('/tasks/:taskId', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;

    const task = await prisma.task.findUnique({
      where: { id: taskId },
      include: {
        events: {
          orderBy: { timestamp: 'asc' },
          take: 100,
        },
      },
    });

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    res.json({ task });
  } catch (error) {
    console.error('Error fetching task:', error);
    res.status(500).json({ error: 'Failed to fetch task' });
  }
});

/**
 * GET /api/tasks/:taskId/events - Get paginated event history
 */
router.get('/tasks/:taskId/events', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    const { limit = '100', offset = '0', type } = req.query;

    const where: Record<string, unknown> = { taskId };
    if (type && typeof type === 'string') {
      where.type = type;
    }

    const events = await prisma.event.findMany({
      where,
      orderBy: { timestamp: 'asc' },
      take: parseInt(limit as string, 10),
      skip: parseInt(offset as string, 10),
    });

    const total = await prisma.event.count({ where });

    res.json({ events, total, limit: parseInt(limit as string, 10), offset: parseInt(offset as string, 10) });
  } catch (error) {
    console.error('Error fetching events:', error);
    res.status(500).json({ error: 'Failed to fetch events' });
  }
});

/**
 * POST /api/agents/:agentId/tasks - Start new task on specific agent
 */
router.post('/agents/:agentId/tasks', async (req: Request, res: Response) => {
  try {
    const { agentId } = req.params;
    const { task, config } = req.body;

    if (!task) {
      res.status(400).json({ error: 'Missing required field: task' });
      return;
    }

    const agent = agentRegistry.get(agentId);
    if (!agent || agent.status !== 'online') {
      res.status(404).json({ error: 'Agent not found or offline' });
      return;
    }

    // Send task request to agent via WebSocket
    io.to(`agent_${agentId}`).emit('start_task', { task, config });

    res.status(202).json({
      message: 'Task request sent to agent',
      agentId,
    });
  } catch (error) {
    console.error('Error starting task:', error);
    res.status(500).json({ error: 'Failed to start task' });
  }
});

/**
 * POST /api/tasks/:taskId/answer - Answer pending question
 */
router.post('/tasks/:taskId/answer', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    const { answer } = req.body;

    if (!answer) {
      res.status(400).json({ error: 'Missing required field: answer' });
      return;
    }

    const task = await prisma.task.findUnique({
      where: { id: taskId },
    });

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const agent = agentRegistry.get(task.agentId);
    if (!agent || agent.status !== 'online') {
      res.status(404).json({ error: 'Agent not found or offline' });
      return;
    }

    // Send answer to agent via WebSocket
    io.to(agent.socketId).emit('answer_question', { taskId, answer });

    res.json({
      success: true,
      message: 'Answer sent to agent',
    });
  } catch (error) {
    console.error('Error answering question:', error);
    res.status(500).json({ error: 'Failed to send answer' });
  }
});

/**
 * POST /api/tasks/:taskId/cancel - Cancel running task
 */
router.post('/tasks/:taskId/cancel', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;

    const task = await prisma.task.findUnique({
      where: { id: taskId },
    });

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const agent = agentRegistry.get(task.agentId);
    if (!agent || agent.status !== 'online') {
      res.status(404).json({ error: 'Agent not found or offline' });
      return;
    }

    // Send cancel request to agent via WebSocket
    io.to(agent.socketId).emit('cancel_task', { taskId });

    res.json({
      success: true,
      message: 'Cancel request sent to agent',
    });
  } catch (error) {
    console.error('Error cancelling task:', error);
    res.status(500).json({ error: 'Failed to cancel task' });
  }
});

export default router;
