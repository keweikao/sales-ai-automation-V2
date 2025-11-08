import fs from 'fs/promises';
import path from 'path';
import { encoding_for_model, get_encoding, Tiktoken } from 'tiktoken';

export const PROJECT_ROOT =
  path.basename(process.cwd()) === '.specify'
    ? path.resolve(process.cwd(), '..')
    : process.cwd();

// Initialize encoder once per process. Prefer Claude 3.5 Sonnet; fallback to cl100k.
const encoder: Tiktoken = (() => {
  try {
    return encoding_for_model('claude-3-5-sonnet-20241022');
  } catch (error) {
    console.warn(
      '[Token] Model claude-3-5-sonnet-20241022 unsupported in tiktoken. Falling back to cl100k_base.'
    );
    return get_encoding('cl100k_base');
  }
})();

// ---------------------------------------------------------------------------
// In-memory cache primitives
// ---------------------------------------------------------------------------
interface CacheEntry {
  content: string;
  timestamp: number; // epoch millis when entry was stored
}

const cache = new Map<string, CacheEntry>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// ---------------------------------------------------------------------------
// Tool routing types
// ---------------------------------------------------------------------------
export type ToolHandler<TInput = unknown, TResult = unknown> = (
  input: TInput
) => Promise<TResult> | TResult;

const toolRegistry = new Map<string, ToolHandler>();

/** Register or override a tool handler (mainly for future extensibility/tests). */
export function registerTool<TInput, TResult>(
  toolName: string,
  handler: ToolHandler<TInput, TResult>
): void {
  toolRegistry.set(toolName, handler as ToolHandler);
}

// ---------------------------------------------------------------------------
// Token counting helpers
// ---------------------------------------------------------------------------
export function countTokens(text: string): number {
  return encoder.encode(text).length;
}

// ---------------------------------------------------------------------------
// MCP tool invocation pipeline
// ---------------------------------------------------------------------------
export async function callMCPTool<T>(
  toolName: string,
  input: unknown
): Promise<T> {
  const startTime = Date.now();

  try {
    console.log(`[MCP] Calling tool: ${toolName}`);
    const result = await executeTool(toolName, input);

    const serialized = safeSerialize(result);
    const tokens = countTokens(serialized);

    await logTokenUsage(toolName, tokens, Date.now() - startTime);
    console.log(
      `[MCP] ${toolName} completed: ${tokens} tokens, ${Date.now() - startTime}ms`
    );

    return result as T;
  } catch (error) {
    console.error(`[MCP] Error in tool ${toolName}:`, error);
    throw error;
  }
}

async function executeTool(toolName: string, input: unknown): Promise<unknown> {
  const handler = toolRegistry.get(toolName);
  if (!handler) {
    throw new Error(`Tool not implemented: ${toolName}`);
  }

  try {
    return await handler(input);
  } catch (error) {
    // Re-throw with more context but preserve original stack
    throw new Error(`Tool ${toolName} failed: ${(error as Error).message}`);
  }
}

function safeSerialize(value: unknown): string {
  try {
    return JSON.stringify(value) ?? '';
  } catch {
    return String(value);
  }
}

// ---------------------------------------------------------------------------
// Markdown reader with caching
// ---------------------------------------------------------------------------
export async function readMarkdownFile(filePath: string): Promise<string> {
  const fullPath = path.isAbsolute(filePath)
    ? filePath
    : path.join(PROJECT_ROOT, filePath);
  const cacheKey = fullPath;

  // Check cache validity
  const cached = cache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    console.log(`[Cache] Hit: ${path.basename(filePath)}`);
    return cached.content;
  }

  // Read from disk with error handling
  try {
    console.log(`[File] Reading: ${filePath}`);
    const content = await fs.readFile(fullPath, 'utf-8');
    cache.set(cacheKey, { content, timestamp: Date.now() });
    return content;
  } catch (error) {
    console.error(`[File] Read error for ${filePath}:`, error);
    throw new Error(`Unable to read file: ${filePath}`);
  }
}

// ---------------------------------------------------------------------------
// Token usage logging
// ---------------------------------------------------------------------------
interface TokenUsageRecord {
  timestamp: string;
  tool: string;
  tokens: number;
  duration: number; // milliseconds
}

export async function logTokenUsage(
  tool: string,
  tokens: number,
  duration: number
): Promise<void> {
  const logPath = path.join(PROJECT_ROOT, '.specify/logs/token-usage.json');
  const record: TokenUsageRecord = {
    timestamp: new Date().toISOString(),
    tool,
    tokens,
    duration,
  };

  try {
    await fs.mkdir(path.dirname(logPath), { recursive: true });

    let records: TokenUsageRecord[] = [];
    try {
      const existing = await fs.readFile(logPath, 'utf-8');
      records = JSON.parse(existing);
      if (!Array.isArray(records)) {
        records = [];
      }
    } catch (error) {
      // File missing or malformed; start fresh but log warning
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        console.warn('[Log] Existing token log invalid, resetting file.');
      }
      records = [];
    }

    records.push(record);
    await fs.writeFile(logPath, JSON.stringify(records, null, 2), 'utf-8');
  } catch (error) {
    console.error('[Log] Error writing token usage:', error);
  }
}

// ---------------------------------------------------------------------------
// Cache management helpers
// ---------------------------------------------------------------------------
export function clearCache(): void {
  cache.clear();
  console.log('[Cache] Cleared');
}

export function pruneCache(): void {
  const now = Date.now();
  for (const [key, entry] of cache.entries()) {
    if (now - entry.timestamp >= CACHE_TTL) {
      cache.delete(key);
    }
  }
}
