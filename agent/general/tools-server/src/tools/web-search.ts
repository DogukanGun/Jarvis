import { Type } from "@sinclair/typebox";
import type { Tool, ToolResult } from "../shared/common.js";
import { jsonResult, readNumberParam, readStringParam } from "../shared/common.js";
import {
  CacheEntry,
  DEFAULT_CACHE_TTL_MINUTES,
  DEFAULT_TIMEOUT_SECONDS,
  normalizeCacheKey,
  readCache,
  readResponseText,
  resolveCacheTtlMs,
  resolveTimeoutSeconds,
  withTimeout,
  writeCache,
} from "../shared/web-shared.js";

const SEARCH_PROVIDERS = ["brave", "perplexity"] as const;
const DEFAULT_SEARCH_COUNT = 5;
const MAX_SEARCH_COUNT = 10;

const BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search";
const DEFAULT_PERPLEXITY_BASE_URL = "https://api.perplexity.ai";

const SEARCH_CACHE = new Map<string, CacheEntry<Record<string, unknown>>>();

const WebSearchSchema = Type.Object({
  query: Type.String({ description: "Search query string." }),
  count: Type.Optional(
    Type.Number({
      description: "Number of results to return (1-10).",
      minimum: 1,
      maximum: MAX_SEARCH_COUNT,
    })
  ),
  provider: Type.Optional(
    Type.String({
      description: 'Search provider: "brave" or "perplexity". Defaults to "brave".',
    })
  ),
  country: Type.Optional(
    Type.String({
      description:
        "2-letter country code for region-specific results (e.g., 'DE', 'US', 'ALL'). Default: 'US'.",
    })
  ),
});

type BraveSearchResult = {
  title?: string;
  url?: string;
  description?: string;
  age?: string;
};

type BraveSearchResponse = {
  web?: {
    results?: BraveSearchResult[];
  };
};

type PerplexitySearchResponse = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
  citations?: string[];
};

function resolveSearchCount(value: unknown, fallback: number): number {
  const parsed = typeof value === "number" && Number.isFinite(value) ? value : fallback;
  const clamped = Math.max(1, Math.min(MAX_SEARCH_COUNT, Math.floor(parsed)));
  return clamped;
}

function resolveSiteName(url: string | undefined): string | undefined {
  if (!url) return undefined;
  try {
    return new URL(url).hostname;
  } catch {
    return undefined;
  }
}

async function runPerplexitySearch(params: {
  query: string;
  apiKey: string;
  timeoutSeconds: number;
}): Promise<{ content: string; citations: string[] }> {
  const endpoint = `${DEFAULT_PERPLEXITY_BASE_URL}/chat/completions`;

  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.apiKey}`,
    },
    body: JSON.stringify({
      model: "sonar-pro",
      messages: [{ role: "user", content: params.query }],
    }),
    signal: withTimeout(undefined, params.timeoutSeconds * 1000),
  });

  if (!res.ok) {
    const detail = await readResponseText(res);
    throw new Error(`Perplexity API error (${res.status}): ${detail || res.statusText}`);
  }

  const data = (await res.json()) as PerplexitySearchResponse;
  const content = data.choices?.[0]?.message?.content ?? "No response";
  const citations = data.citations ?? [];

  return { content, citations };
}

async function runWebSearch(params: {
  query: string;
  count: number;
  apiKey: string;
  timeoutSeconds: number;
  cacheTtlMs: number;
  provider: (typeof SEARCH_PROVIDERS)[number];
  country?: string;
}): Promise<Record<string, unknown>> {
  const cacheKey = normalizeCacheKey(
    `${params.provider}:${params.query}:${params.count}:${params.country || "default"}`
  );
  const cached = readCache(SEARCH_CACHE, cacheKey);
  if (cached) return { ...cached.value, cached: true };

  const start = Date.now();

  if (params.provider === "perplexity") {
    const { content, citations } = await runPerplexitySearch({
      query: params.query,
      apiKey: params.apiKey,
      timeoutSeconds: params.timeoutSeconds,
    });

    const payload = {
      query: params.query,
      provider: params.provider,
      tookMs: Date.now() - start,
      content,
      citations,
    };
    writeCache(SEARCH_CACHE, cacheKey, payload, params.cacheTtlMs);
    return payload;
  }

  // Brave search
  const url = new URL(BRAVE_SEARCH_ENDPOINT);
  url.searchParams.set("q", params.query);
  url.searchParams.set("count", String(params.count));
  if (params.country) {
    url.searchParams.set("country", params.country);
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-Subscription-Token": params.apiKey,
    },
    signal: withTimeout(undefined, params.timeoutSeconds * 1000),
  });

  if (!res.ok) {
    const detail = await readResponseText(res);
    throw new Error(`Brave Search API error (${res.status}): ${detail || res.statusText}`);
  }

  const data = (await res.json()) as BraveSearchResponse;
  const results = Array.isArray(data.web?.results) ? (data.web?.results ?? []) : [];
  const mapped = results.map((entry) => ({
    title: entry.title ?? "",
    url: entry.url ?? "",
    description: entry.description ?? "",
    published: entry.age ?? undefined,
    siteName: resolveSiteName(entry.url ?? ""),
  }));

  const payload = {
    query: params.query,
    provider: params.provider,
    count: mapped.length,
    tookMs: Date.now() - start,
    results: mapped,
  };
  writeCache(SEARCH_CACHE, cacheKey, payload, params.cacheTtlMs);
  return payload;
}

export function createWebSearchTool(): Tool {
  return {
    label: "Web Search",
    name: "web_search",
    description:
      "Search the web using Brave Search or Perplexity API. Returns titles, URLs, and snippets for research.",
    parameters: WebSearchSchema,
    execute: async (args): Promise<ToolResult> => {
      const params = args as Record<string, unknown>;
      const query = readStringParam(params, "query", { required: true });
      const count = readNumberParam(params, "count", { integer: true });
      const providerRaw = readStringParam(params, "provider")?.toLowerCase();
      const provider: (typeof SEARCH_PROVIDERS)[number] =
        providerRaw === "perplexity" ? "perplexity" : "brave";
      const country = readStringParam(params, "country");

      const apiKey =
        provider === "perplexity"
          ? process.env.PERPLEXITY_API_KEY
          : process.env.BRAVE_API_KEY;

      if (!apiKey) {
        return jsonResult({
          error: `missing_${provider}_api_key`,
          message: `web_search needs a ${provider === "perplexity" ? "PERPLEXITY_API_KEY" : "BRAVE_API_KEY"} environment variable.`,
        });
      }

      const result = await runWebSearch({
        query,
        count: resolveSearchCount(count, DEFAULT_SEARCH_COUNT),
        apiKey,
        timeoutSeconds: resolveTimeoutSeconds(undefined, DEFAULT_TIMEOUT_SECONDS),
        cacheTtlMs: resolveCacheTtlMs(undefined, DEFAULT_CACHE_TTL_MINUTES),
        provider,
        country,
      });
      return jsonResult(result);
    },
  };
}
