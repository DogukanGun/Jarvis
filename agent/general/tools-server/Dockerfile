FROM mcr.microsoft.com/playwright:v1.49.0-noble

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile || pnpm install

# Install Playwright browsers
RUN npx playwright install chromium

# Copy source code
COPY tsconfig.json ./
COPY src ./src

# Build TypeScript
RUN pnpm build

# Expose port
EXPOSE 3000

# Start the server
CMD ["node", "dist/index.js"]
