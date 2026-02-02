/**
 * PM2 Ecosystem Configuration
 *
 * Run with: pm2 start ecosystem.config.cjs
 */

module.exports = {
  apps: [
    // Observation Hub
    {
      name: 'observation-hub',
      cwd: './packages/observation-hub',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 4000,
        DATABASE_URL: 'postgresql://qwen:qwen@localhost:5432/qwen_observation',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },

    // Qwen Agent 1
    {
      name: 'qwen-agent-1',
      cwd: './packages/http-wrapper',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 3001,
        AGENT_ID: 'qwen-1',
        AGENT_NAME: 'Qwen Agent 1',
        OBSERVATION_HUB_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },

    // Qwen Agent 2
    {
      name: 'qwen-agent-2',
      cwd: './packages/http-wrapper',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 3002,
        AGENT_ID: 'qwen-2',
        AGENT_NAME: 'Qwen Agent 2',
        OBSERVATION_HUB_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },

    // Qwen Agent 3
    {
      name: 'qwen-agent-3',
      cwd: './packages/http-wrapper',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 3003,
        AGENT_ID: 'qwen-3',
        AGENT_NAME: 'Qwen Agent 3',
        OBSERVATION_HUB_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },

    // Qwen Agent 4
    {
      name: 'qwen-agent-4',
      cwd: './packages/http-wrapper',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 3004,
        AGENT_ID: 'qwen-4',
        AGENT_NAME: 'Qwen Agent 4',
        OBSERVATION_HUB_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },

    // Qwen Agent 5
    {
      name: 'qwen-agent-5',
      cwd: './packages/http-wrapper',
      script: 'dist/server.js',
      node_args: '--experimental-specifier-resolution=node',
      env: {
        PORT: 3005,
        AGENT_ID: 'qwen-5',
        AGENT_NAME: 'Qwen Agent 5',
        OBSERVATION_HUB_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
    },
  ],
};
