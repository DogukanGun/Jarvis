/**
 * Jarvis Group Communication Layer - Web App Backend
 * Express.js server that proxies to the router and provides event streaming
 */

const express = require('express');
const cors = require('cors');
const axios = require('axios');
const { Kafka } = require('kafkajs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;
const ROUTER_URL = process.env.ROUTER_URL || 'http://localhost:8080';
const KAFKA_BROKERS = (process.env.KAFKA_BROKERS || 'localhost:9092').split(',');
const GROUP_ID = process.env.GROUP_ID || 'jarvis-main';

// Middleware
app.use(cors());
app.use(express.json());

// Store for SSE clients
const clients = new Set();

// Kafka setup
const kafka = new Kafka({
  clientId: 'web-app-consumer',
  brokers: KAFKA_BROKERS,
});

let consumer;

// Helper function to log
const log = (msg, data = '') => {
  console.log(`[${new Date().toISOString()}] ${msg}`, data ? JSON.stringify(data) : '');
};

// Initialize Kafka consumer
async function initKafka() {
  try {
    consumer = kafka.consumer({ groupId: `web-app-${GROUP_ID}` });
    await consumer.connect();

    const topics = [`group.${GROUP_ID}.events`];
    await consumer.subscribe({ topics, fromBeginning: false });

    log(`Kafka consumer connected, subscribed to ${topics.join(', ')}`);

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        try {
          const envelope = JSON.parse(message.value.toString());
          log(`Event received: ${envelope.type}`);

          // Broadcast to all SSE clients
          broadcastEvent(envelope);
        } catch (err) {
          log('Error parsing Kafka message:', err.message);
        }
      },
    });
  } catch (err) {
    log('Kafka initialization error:', err.message);
  }
}

// Broadcast event to all SSE clients
function broadcastEvent(envelope) {
  const clients_array = Array.from(clients);
  log(`Broadcasting to ${clients_array.length} clients`);

  clients_array.forEach(client => {
    try {
      client.write(`data: ${JSON.stringify(envelope)}\n\n`);
    } catch (err) {
      clients.delete(client);
      log('Error writing to client, removed from subscribers');
    }
  });
}

// ==================== API ENDPOINTS ====================

/**
 * Health check
 */
app.get('/api/health', async (req, res) => {
  try {
    const routerHealth = await axios.get(`${ROUTER_URL}/health`, { timeout: 5000 });
    res.json({
      status: 'healthy',
      router: routerHealth.data,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    res.status(503).json({
      status: 'unhealthy',
      error: err.message,
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Send message to router
 */
app.post('/api/message', async (req, res) => {
  try {
    const { message, imageData } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    log(`Sending message: ${message.substring(0, 50)}...`);

    const response = await axios.post(
      `${ROUTER_URL}/message`,
      { message, image_data: imageData },
      { timeout: 30000 }
    );

    res.json({
      success: true,
      response: response.data.response,
      error: response.data.error || null,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    log('Error sending message:', err.message);
    res.status(err.response?.status || 500).json({
      success: false,
      error: err.message,
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Get orchestrator status
 */
app.get('/api/orchestrator/status', async (req, res) => {
  try {
    const response = await axios.get(`${ROUTER_URL}/orchestrator/status`, { timeout: 5000 });
    res.json(response.data);
  } catch (err) {
    log('Error getting orchestrator status:', err.message);
    res.status(err.response?.status || 500).json({
      error: err.message,
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Server-Sent Events endpoint for real-time event streaming
 */
app.get('/api/events/stream', (req, res) => {
  log('New SSE client connected');

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  // Send initial connection message
  res.write(`data: ${JSON.stringify({ type: 'connection.established', message: 'Connected to event stream' })}\n\n`);

  // Add to clients set
  clients.add(res);

  // Handle client disconnect
  req.on('close', () => {
    clients.delete(res);
    log(`SSE client disconnected, ${clients.size} remaining`);
    res.end();
  });

  // Send heartbeat every 30 seconds
  const heartbeat = setInterval(() => {
    try {
      res.write(`data: ${JSON.stringify({ type: 'heartbeat', timestamp: new Date().toISOString() })}\n\n`);
    } catch (err) {
      clearInterval(heartbeat);
      clients.delete(res);
    }
  }, 30000);
});

/**
 * Publish approval decision
 */
app.post('/api/approval/:approvalId/:decision', async (req, res) => {
  try {
    const { approvalId, decision } = req.params;
    const { reason } = req.body;

    if (!['grant', 'deny'].includes(decision)) {
      return res.status(400).json({ error: 'Decision must be grant or deny' });
    }

    log(`Publishing approval ${decision}: ${approvalId}`);

    // Create envelope and publish to Kafka
    if (consumer && kafka) {
      const producer = kafka.producer();
      await producer.connect();

      const eventType = decision === 'grant' ? 'approval.granted' : 'approval.denied';
      const envelope = {
        group_id: GROUP_ID,
        message_id: generateId(),
        timestamp: new Date().toISOString(),
        thread_id: generateId(),
        sender: {
          id: 'web-app-user',
          role: 'OWNER',
          agent: 'web-app',
        },
        type: eventType,
        payload: {
          approval_id: approvalId,
          reason: reason || `User ${decision}d the approval`,
        },
        version: '1.0',
      };

      await producer.send({
        topic: `group.${GROUP_ID}.events`,
        messages: [
          {
            key: generateId(),
            value: JSON.stringify(envelope),
          },
        ],
      });

      await producer.disconnect();

      res.json({
        success: true,
        message: `Approval ${decision} published`,
        timestamp: new Date().toISOString(),
      });
    } else {
      throw new Error('Kafka not initialized');
    }
  } catch (err) {
    log('Error publishing approval:', err.message);
    res.status(500).json({
      success: false,
      error: err.message,
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Get system configuration
 */
app.get('/api/config', (req, res) => {
  res.json({
    routerUrl: ROUTER_URL,
    kafkaBrokers: KAFKA_BROKERS,
    groupId: GROUP_ID,
    timestamp: new Date().toISOString(),
  });
});

/**
 * Error handling middleware
 */
app.use((err, req, res, next) => {
  log('Error:', err.message);
  res.status(500).json({
    error: err.message,
    timestamp: new Date().toISOString(),
  });
});

/**
 * 404 handler
 */
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    path: req.path,
    timestamp: new Date().toISOString(),
  });
});

// Helper function to generate IDs
function generateId() {
  return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

// ==================== SERVER STARTUP ====================

async function start() {
  try {
    // Initialize Kafka
    await initKafka();

    // Start HTTP server
    app.listen(PORT, () => {
      log(`Web app backend started on port ${PORT}`);
      log(`Router URL: ${ROUTER_URL}`);
      log(`Kafka Brokers: ${KAFKA_BROKERS.join(',')}`);
      log(`Group ID: ${GROUP_ID}`);
    });
  } catch (err) {
    log('Failed to start server:', err.message);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  log('Shutting down gracefully...');
  if (consumer) {
    await consumer.disconnect();
  }
  process.exit(0);
});

start();
