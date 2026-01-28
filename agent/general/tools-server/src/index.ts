import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { createToolRegistry, getToolList } from "./tools/index.js";

const app = new Hono();
const toolRegistry = createToolRegistry();

// Health check endpoint
app.get("/health", (c) => {
  return c.json({ status: "ok", timestamp: new Date().toISOString() });
});

// List all available tools
app.get("/tools", (c) => {
  const tools = getToolList(toolRegistry);
  return c.json({ tools });
});

// Execute a specific tool
app.post("/tools/:toolName", async (c) => {
  const toolName = c.req.param("toolName");
  const tool = toolRegistry.get(toolName);

  if (!tool) {
    return c.json(
      { success: false, error: `Tool not found: ${toolName}` },
      404
    );
  }

  try {
    const body = await c.req.json();
    const args = body.args ?? body ?? {};
    const result = await tool.execute(args);

    return c.json({
      success: true,
      toolName,
      result: result.details ?? result.content,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return c.json({ success: false, error: message }, 500);
  }
});

const port = parseInt(process.env.PORT ?? "3000", 10);

console.log(`Starting tool server on port ${port}...`);
console.log(`Available tools: ${Array.from(toolRegistry.keys()).join(", ")}`);

serve({
  fetch: app.fetch,
  port,
});

console.log(`Tool server running at http://localhost:${port}`);
