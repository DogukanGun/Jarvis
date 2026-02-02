import { Type } from "@sinclair/typebox";
import type { Tool, ToolResult } from "../shared/common.js";
import { jsonResult, readStringParam, readNumberParam } from "../shared/common.js";

// Lazy load playwright to avoid startup cost
let playwrightModule: typeof import("playwright") | null = null;
let browserInstance: import("playwright").Browser | null = null;
let browserContext: import("playwright").BrowserContext | null = null;

async function getPlaywright() {
  if (!playwrightModule) {
    playwrightModule = await import("playwright");
  }
  return playwrightModule;
}

async function getBrowser() {
  const pw = await getPlaywright();
  if (!browserInstance) {
    browserInstance = await pw.chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });
  }
  return browserInstance;
}

async function getContext() {
  if (!browserContext) {
    const browser = await getBrowser();
    browserContext = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    });
  }
  return browserContext;
}

// Track pages by ID
const pages = new Map<string, import("playwright").Page>();
let pageIdCounter = 0;

function generatePageId(): string {
  return `page_${++pageIdCounter}`;
}

const BrowserSchema = Type.Object({
  action: Type.String({
    description:
      'Browser action: "status", "open", "close", "navigate", "snapshot", "screenshot", "click", "type", "tabs"',
  }),
  url: Type.Optional(Type.String({ description: "URL to navigate to (for open/navigate)" })),
  pageId: Type.Optional(Type.String({ description: "Page ID to operate on" })),
  selector: Type.Optional(Type.String({ description: "CSS selector for click/type actions" })),
  text: Type.Optional(Type.String({ description: "Text to type (for type action)" })),
  fullPage: Type.Optional(Type.Boolean({ description: "Take full page screenshot" })),
});

async function handleBrowserAction(params: Record<string, unknown>): Promise<unknown> {
  const action = readStringParam(params, "action", { required: true });

  switch (action) {
    case "status": {
      return {
        running: browserInstance !== null,
        pagesOpen: pages.size,
        pageIds: Array.from(pages.keys()),
      };
    }

    case "tabs": {
      const tabs = [];
      for (const [id, page] of pages) {
        tabs.push({
          pageId: id,
          url: page.url(),
          title: await page.title(),
        });
      }
      return { tabs };
    }

    case "open": {
      const url = readStringParam(params, "url", { required: true });
      const context = await getContext();
      const page = await context.newPage();
      const pageId = generatePageId();
      pages.set(pageId, page);

      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

      return {
        pageId,
        url: page.url(),
        title: await page.title(),
      };
    }

    case "close": {
      const pageId = readStringParam(params, "pageId");
      if (pageId) {
        const page = pages.get(pageId);
        if (page) {
          await page.close();
          pages.delete(pageId);
          return { closed: true, pageId };
        }
        throw new Error(`Page not found: ${pageId}`);
      }
      // Close all pages
      for (const [id, page] of pages) {
        await page.close();
        pages.delete(id);
      }
      return { closed: true, all: true };
    }

    case "navigate": {
      const pageId = readStringParam(params, "pageId", { required: true });
      const url = readStringParam(params, "url", { required: true });
      const page = pages.get(pageId);
      if (!page) throw new Error(`Page not found: ${pageId}`);

      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
      return {
        pageId,
        url: page.url(),
        title: await page.title(),
      };
    }

    case "snapshot": {
      const pageId = readStringParam(params, "pageId", { required: true });
      const page = pages.get(pageId);
      if (!page) throw new Error(`Page not found: ${pageId}`);

      const title = await page.title();
      const url = page.url();

      // Get text content as a simplified snapshot
      const content = await page.evaluate(() => {
        const getText = (node: Node): string => {
          if (node.nodeType === Node.TEXT_NODE) {
            return node.textContent?.trim() || "";
          }
          if (node.nodeType !== Node.ELEMENT_NODE) return "";

          const el = node as Element;
          const tag = el.tagName.toLowerCase();

          // Skip hidden elements
          if (tag === "script" || tag === "style" || tag === "noscript") {
            return "";
          }

          const children = Array.from(node.childNodes)
            .map(getText)
            .filter(Boolean)
            .join(" ");

          // Add structure hints
          if (tag === "h1" || tag === "h2" || tag === "h3") {
            return `\n## ${children}\n`;
          }
          if (tag === "p" || tag === "div") {
            return `\n${children}\n`;
          }
          if (tag === "li") {
            return `\n- ${children}`;
          }
          if (tag === "a") {
            const href = el.getAttribute("href");
            return href ? `[${children}](${href})` : children;
          }
          if (tag === "button" || tag === "input") {
            const text = el.getAttribute("value") || el.getAttribute("placeholder") || children;
            return `[${tag}: ${text}]`;
          }

          return children;
        };

        return getText(document.body)
          .replace(/\n{3,}/g, "\n\n")
          .trim()
          .slice(0, 50000);
      });

      // Get interactive elements
      const interactiveElements = await page.evaluate(() => {
        const elements: Array<{ tag: string; text: string; selector: string }> = [];
        const selectors = [
          "a",
          "button",
          'input[type="text"]',
          'input[type="submit"]',
          'input[type="button"]',
          "textarea",
          "select",
          '[role="button"]',
          '[onclick]',
        ];

        for (const selector of selectors) {
          document.querySelectorAll(selector).forEach((el, idx) => {
            const text =
              el.textContent?.trim().slice(0, 50) ||
              el.getAttribute("value") ||
              el.getAttribute("placeholder") ||
              el.getAttribute("aria-label") ||
              "";
            if (text) {
              elements.push({
                tag: el.tagName.toLowerCase(),
                text,
                selector: `${selector}:nth-of-type(${idx + 1})`,
              });
            }
          });
        }

        return elements.slice(0, 50);
      });

      return {
        pageId,
        url,
        title,
        content,
        interactiveElements,
      };
    }

    case "screenshot": {
      const pageId = readStringParam(params, "pageId", { required: true });
      const fullPage = params.fullPage === true;
      const page = pages.get(pageId);
      if (!page) throw new Error(`Page not found: ${pageId}`);

      const buffer = await page.screenshot({
        fullPage,
        type: "png",
      });

      return {
        pageId,
        screenshot: buffer.toString("base64"),
        mimeType: "image/png",
        fullPage,
      };
    }

    case "click": {
      const pageId = readStringParam(params, "pageId", { required: true });
      const selector = readStringParam(params, "selector", { required: true });
      const page = pages.get(pageId);
      if (!page) throw new Error(`Page not found: ${pageId}`);

      await page.click(selector, { timeout: 10000 });
      await page.waitForLoadState("domcontentloaded", { timeout: 10000 }).catch(() => {});

      return {
        pageId,
        clicked: selector,
        url: page.url(),
        title: await page.title(),
      };
    }

    case "type": {
      const pageId = readStringParam(params, "pageId", { required: true });
      const selector = readStringParam(params, "selector", { required: true });
      const text = readStringParam(params, "text", { required: true });
      const page = pages.get(pageId);
      if (!page) throw new Error(`Page not found: ${pageId}`);

      await page.fill(selector, text, { timeout: 10000 });

      return {
        pageId,
        typed: text,
        selector,
      };
    }

    default:
      throw new Error(`Unknown browser action: ${action}`);
  }
}

export function createBrowserTool(): Tool {
  return {
    label: "Browser",
    name: "browser",
    description: `Control a headless browser for web automation. Actions:
- status: Get browser status and open pages
- tabs: List all open pages with URLs and titles
- open: Open a new page with a URL (returns pageId)
- close: Close a page by pageId (or all if no pageId)
- navigate: Navigate a page to a new URL
- snapshot: Get page content and interactive elements
- screenshot: Take a screenshot (returns base64)
- click: Click an element by CSS selector
- type: Type text into an input field`,
    parameters: BrowserSchema,
    execute: async (args): Promise<ToolResult> => {
      const params = args as Record<string, unknown>;
      const result = await handleBrowserAction(params);
      return jsonResult(result);
    },
  };
}

// Cleanup on process exit
process.on("beforeExit", async () => {
  if (browserInstance) {
    await browserInstance.close();
  }
});
