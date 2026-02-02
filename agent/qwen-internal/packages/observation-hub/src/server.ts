/**
 * Observation Hub - Main Server
 *
 * Aggregates events from multiple Qwen agents and provides REST + WebSocket API
 * for external observation (e.g., phone app).
 */

import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { Server as SocketServer } from 'socket.io';
import { PrismaClient } from '@prisma/client';
import { v4 as uuidv4 } from 'uuid';
import { agentRegistry } from './agent-registry.js';
import routes, { initializeRoutes } from './api/routes.js';
import type {
  TaskCreatedPayload,
  TaskUpdatedPayload,
  EventPayload,
  ClientToServerEvents,
  ServerToClientEvents,
  AgentToHubEvents,
} from './types.js';

const PORT = process.env['PORT'] ? parseInt(process.env['PORT']) : 4000;
const DATABASE_URL = process.env['DATABASE_URL'] || 'postgresql://qwen:qwen@localhost:5432/qwen_observation';

// Initialize Prisma
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: DATABASE_URL,
    },
  },
});

// Initialize Express
const app = express();
app.use(cors());
app.use(express.json());

// Request logging
app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health check
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    timestamp: Date.now(),
    connectedAgents: agentRegistry.getOnline().length,
  });
});

// Create HTTP server
const httpServer = createServer(app);

// Initialize Socket.IO with custom path
const io = new SocketServer<ClientToServerEvents & AgentToHubEvents, ServerToClientEvents>(httpServer, {
  path: '/ws',
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
});

// Initialize API routes
app.use('/api', initializeRoutes(prisma, io));

/**
 * Handle WebSocket connections
 */
io.on('connection', (socket) => {
  console.log(`[Socket] New connection: ${socket.id}`);

  // Get agent info from auth
  const { agentId, agentName } = socket.handshake.auth as { agentId?: string; agentName?: string };

  // Handle agent registration
  socket.on('agent_register', async (data: { agentId: string; agentName?: string }) => {
    const agent = agentRegistry.register(data.agentId, socket.id, data.agentName);

    // Join agent-specific room
    socket.join(`agent_${data.agentId}`);

    // Upsert agent in database
    await prisma.agent.upsert({
      where: { id: data.agentId },
      update: {
        name: data.agentName,
        status: 'online',
        lastSeen: new Date(),
      },
      create: {
        id: data.agentId,
        name: data.agentName,
        status: 'online',
      },
    });

    // Broadcast to all subscribers
    io.to('all').emit('agent_connected', agent);

    console.log(`[Socket] Agent registered: ${data.agentId}`);
  });

  // If agent info provided in auth, auto-register
  if (agentId) {
    const agent = agentRegistry.register(agentId, socket.id, agentName);
    socket.join(`agent_${agentId}`);

    prisma.agent.upsert({
      where: { id: agentId },
      update: {
        name: agentName,
        status: 'online',
        lastSeen: new Date(),
      },
      create: {
        id: agentId,
        name: agentName,
        status: 'online',
      },
    }).catch(err => console.error('Failed to upsert agent:', err));

    io.to('all').emit('agent_connected', agent);
  }

  // Handle task created events from agents
  socket.on('task_created', async (payload: TaskCreatedPayload) => {
    console.log(`[Socket] Task created: ${payload.taskId} from ${payload.agentId}`);

    // Update agent's last seen and active tasks
    agentRegistry.updateLastSeen(payload.agentId);
    agentRegistry.incrementActiveTasks(payload.agentId);

    // Store in database
    const task = await prisma.task.create({
      data: {
        id: payload.taskId,
        agentId: payload.agentId,
        description: payload.description,
        status: payload.status,
        createdAt: new Date(payload.createdAt),
      },
    });

    // Broadcast to subscribers
    io.to('all').to(`agent_${payload.agentId}`).to(`task_${payload.taskId}`).emit('task_created', {
      id: task.id,
      agentId: task.agentId,
      description: task.description,
      status: task.status as any,
      createdAt: task.createdAt,
    });
  });

  // Handle task updated events from agents
  socket.on('task_updated', async (payload: TaskUpdatedPayload) => {
    console.log(`[Socket] Task updated: ${payload.taskId} status=${payload.status}`);

    // Update agent's last seen
    agentRegistry.updateLastSeen(payload.agentId);

    // Decrement active tasks if task completed/failed/cancelled
    if (['completed', 'error', 'cancelled'].includes(payload.status)) {
      agentRegistry.decrementActiveTasks(payload.agentId);
    }

    // Update in database
    const task = await prisma.task.update({
      where: { id: payload.taskId },
      data: {
        status: payload.status,
        startedAt: payload.startedAt ? new Date(payload.startedAt) : undefined,
        completedAt: payload.completedAt ? new Date(payload.completedAt) : undefined,
        result: payload.result,
        error: payload.error,
      },
    });

    // Broadcast to subscribers
    io.to('all').to(`agent_${payload.agentId}`).to(`task_${payload.taskId}`).emit('task_updated', {
      id: task.id,
      agentId: task.agentId,
      description: task.description,
      status: task.status as any,
      createdAt: task.createdAt,
      startedAt: task.startedAt ?? undefined,
      completedAt: task.completedAt ?? undefined,
      result: task.result ?? undefined,
      error: task.error ?? undefined,
    });
  });

  // Handle new events from agents
  socket.on('new_event', async (payload: EventPayload) => {
    // Update agent's last seen
    agentRegistry.updateLastSeen(payload.agentId);

    // Store in database
    const event = await prisma.event.create({
      data: {
        id: uuidv4(),
        taskId: payload.taskId,
        type: payload.event.type,
        data: payload.event as any,
        timestamp: new Date(payload.event.timestamp),
      },
    });

    // Broadcast to subscribers
    io.to('all').to(`agent_${payload.agentId}`).to(`task_${payload.taskId}`).emit('new_event', {
      id: event.id,
      taskId: event.taskId,
      type: event.type as any,
      data: event.data as any,
      timestamp: event.timestamp,
    });
  });

  // Handle task deleted events
  socket.on('task_deleted', async (data: { taskId: string; agentId: string }) => {
    console.log(`[Socket] Task deleted: ${data.taskId}`);

    // Delete events first (due to foreign key)
    await prisma.event.deleteMany({
      where: { taskId: data.taskId },
    });

    // Delete task
    await prisma.task.delete({
      where: { id: data.taskId },
    }).catch(() => {
      // Task might not exist in DB
    });
  });

  // Client subscription handlers
  socket.on('join_all', () => {
    socket.join('all');
    console.log(`[Socket] ${socket.id} joined 'all' room`);
  });

  socket.on('join_agent', (agentId: string) => {
    socket.join(`agent_${agentId}`);
    console.log(`[Socket] ${socket.id} joined 'agent_${agentId}' room`);
  });

  socket.on('join_task', (taskId: string) => {
    socket.join(`task_${taskId}`);
    console.log(`[Socket] ${socket.id} joined 'task_${taskId}' room`);
  });

  socket.on('leave_all', () => {
    socket.leave('all');
  });

  socket.on('leave_agent', (agentId: string) => {
    socket.leave(`agent_${agentId}`);
  });

  socket.on('leave_task', (taskId: string) => {
    socket.leave(`task_${taskId}`);
  });

  // Handle disconnect
  socket.on('disconnect', async () => {
    const agent = agentRegistry.unregisterBySocketId(socket.id);

    if (agent) {
      // Update agent status in database
      await prisma.agent.update({
        where: { id: agent.id },
        data: {
          status: 'offline',
          lastSeen: new Date(),
        },
      }).catch(() => {
        // Agent might not exist in DB
      });

      // Broadcast to subscribers
      io.to('all').emit('agent_disconnected', agent.id);
    }

    console.log(`[Socket] Disconnected: ${socket.id}`);
  });
});

/**
 * Start the server
 */
async function start() {
  try {
    // Connect to database
    await prisma.$connect();
    console.log('Connected to PostgreSQL');

    // Start HTTP server
    httpServer.listen(PORT, () => {
      console.log(`\nObservation Hub listening on port ${PORT}`);
      console.log(`  Health: http://localhost:${PORT}/health`);
      console.log(`  REST API: http://localhost:${PORT}/api`);
      console.log(`  WebSocket: ws://localhost:${PORT}/ws`);
      console.log('');
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

/**
 * Graceful shutdown
 */
async function shutdown() {
  console.log('\nShutting down...');

  // Close all socket connections
  io.close();

  // Close HTTP server
  httpServer.close();

  // Disconnect from database
  await prisma.$disconnect();

  console.log('Server stopped');
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

// Start the server
start();
