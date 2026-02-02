import type { Tool } from "../shared/common.js";
import { createWebSearchTool } from "./web-search.js";
import { createWebFetchTool } from "./web-fetch.js";
import { createExecTool } from "./exec.js";
import { createBrowserTool } from "./browser.js";
import { createCronTool } from "./cron.js";

export function createToolRegistry(): Map<string, Tool> {
  const tools = new Map<string, Tool>();

  const webSearch = createWebSearchTool();
  const webFetch = createWebFetchTool();
  const exec = createExecTool();
  const browser = createBrowserTool();
  const cron = createCronTool();

  tools.set(webSearch.name, webSearch);
  tools.set(webFetch.name, webFetch);
  tools.set(exec.name, exec);
  tools.set(browser.name, browser);
  tools.set(cron.name, cron);

  return tools;
}

export function getToolList(registry: Map<string, Tool>) {
  return Array.from(registry.values()).map((tool) => ({
    name: tool.name,
    label: tool.label,
    description: tool.description,
    parameters: tool.parameters,
  }));
}
