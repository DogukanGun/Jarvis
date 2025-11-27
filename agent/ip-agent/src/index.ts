import express, { Application } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import routes from './api/routes';
import { initializeStoryClient } from './config/storyClient';
import { IPAgentConsumer } from './kafka/consumer';

// Load environment variables
dotenv.config();

const app: Application = express();
const PORT = process.env.PORT || 8085;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' })); // Increase limit for base64 images
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Routes
app.use('/', routes);

// Global error handler
app.use((err: any, req: any, res: any, next: any) => {
  console.error('Global error handler:', err);
  res.status(500).json({
    success: false,
    error: err.message || 'Internal server error',
  });
});

// Initialize and start server
async function startServer() {
  try {
    // Initialize Story Protocol client
    console.log('Initializing Story Protocol client...');
    initializeStoryClient();
    console.log('✓ Story Protocol client ready');

    // Start HTTP server
    app.listen(PORT, () => {
      console.log(`\n=================================`);
      console.log(`IP Agent Service`);
      console.log(`=================================`);
      console.log(`Server running on port ${PORT}`);
      console.log(`Health check: http://localhost:${PORT}/health`);
      console.log(`API endpoint: http://localhost:${PORT}/api/v1/ip/register`);
      console.log(`=================================\n`);
    });

    // Initialize Kafka consumer (optional)
    if (process.env.ENABLE_KAFKA === 'true') {
      console.log('Starting Kafka consumer...');
      const consumer = new IPAgentConsumer();
      await consumer.connect();
      await consumer.start();
      console.log('✓ Kafka consumer started');

      // Graceful shutdown
      process.on('SIGTERM', async () => {
        console.log('SIGTERM received, shutting down...');
        await consumer.disconnect();
        process.exit(0);
      });

      process.on('SIGINT', async () => {
        console.log('SIGINT received, shutting down...');
        await consumer.disconnect();
        process.exit(0);
      });
    } else {
      console.log('Kafka integration disabled (set ENABLE_KAFKA=true to enable)');
    }
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

