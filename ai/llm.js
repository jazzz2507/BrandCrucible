import { GoogleGenAI } from '@google/genai';
import { z } from 'zod';

const model = process.env.GEMINI_MODEL || 'gemini-3.7-flash';

export async function callLLM(systemPrompt, userInput, schema) {
  if (!process.env.GEMINI_API_KEY) {
    throw new Error(
      'GEMINI_API_KEY is required. Set it in the environment before running a stage or pipeline.'
    );
  }

  const client = new GoogleGenAI({
    apiKey: process.env.GEMINI_API_KEY,
  });

  const jsonSchema = cleanProviderSchema(z.toJSONSchema(schema));

  let repairNote = '';
  let lastError;

  const maxAttempts = 8;
  const max429Retries = 3;
  let rateLimitRetries = 0;

  function extractRetryDelay(err) {
    const parseDelay = (val) => {
      if (typeof val === 'number' && !isNaN(val) && val > 0) return val;
      if (typeof val === 'string') {
        const match = val.match(/([0-9.]+)\s*s?/i);
        if (match) {
          const num = parseFloat(match[1]);
          if (!isNaN(num) && num > 0) return num;
        }
      }
      if (typeof val === 'object' && val !== null) {
        const seconds = Number(val.seconds) || 0;
        const nanos = Number(val.nanos) || 0;
        const total = seconds + nanos / 1e9;
        if (total > 0) return total;
      }
      return null;
    };

    const detailsSources = [err?.errorDetails, err?.details];
    for (const source of detailsSources) {
      if (!source) continue;
      const items = Array.isArray(source) ? source : [source];
      for (const item of items) {
        if (!item || typeof item !== 'object') continue;
        if (item.retryDelay !== undefined) {
          const parsed = parseDelay(item.retryDelay);
          if (parsed !== null) return parsed;
        }
        if (item.retry_delay !== undefined) {
          const parsed = parseDelay(item.retry_delay);
          if (parsed !== null) return parsed;
        }
        if (item.metadata?.retryDelay !== undefined) {
          const parsed = parseDelay(item.metadata.retryDelay);
          if (parsed !== null) return parsed;
        }
        if (item.metadata?.['retry-delay'] !== undefined) {
          const parsed = parseDelay(item.metadata['retry-delay']);
          if (parsed !== null) return parsed;
        }
      }
    }

    if (typeof err?.message === 'string') {
      const fieldMatch = err.message.match(
        /(?:retryDelay|retry_delay)["']?\s*[:=]\s*["']?([0-9.]+)\s*s?/i
      );
      if (fieldMatch) {
        const num = parseFloat(fieldMatch[1]);
        if (!isNaN(num) && num > 0) return num;
      }

      const textMatch = err.message.match(
        /(?:retry|wait)\s+(?:in|after)\s+([0-9.]+)\s*(?:s|seconds)?/i
      );
      if (textMatch) {
        const num = parseFloat(textMatch[1]);
        if (!isNaN(num) && num > 0) return num;
      }
    }

    return null;
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await client.models.generateContent({
        model,
        contents: [
          {
            role: 'user',
            parts: [
              {
                text:
                  `${systemPrompt}\n\n` +
                  `Return only a JSON object that conforms exactly to this JSON Schema:\n` +
                  `${JSON.stringify(jsonSchema)}\n\n` +
                  `Input:\n` +
                  `${typeof userInput === 'string' ? userInput : JSON.stringify(userInput)}` +
                  repairNote,
              },
            ],
          },
        ],
        config: {
          responseMimeType: 'application/json',
          responseSchema: jsonSchema,
        },
      });

      const content = response.text;

      if (!content) {
        throw new Error('Provider returned an empty response.');
      }

      const parsed = JSON.parse(content);

      const validated = schema.safeParse(parsed);

      if (!validated.success) {
        throw new Error(
          `Schema validation failed: ${validated.error.message}`
        );
      }

      return validated.data;

    } catch (error) {
      lastError = error;

      // 1. Separate check for 429 RESOURCE_EXHAUSTED rate-limit errors
      if (error?.status === 429) {
        if (rateLimitRetries < max429Retries && attempt < maxAttempts) {
          rateLimitRetries += 1;

          // 2. Extract Gemini's suggested retry delay if present
          const suggestedDelaySec = extractRetryDelay(error);

          // 3. Fall back to sensible default backoff specifically for 429: 20s, 40s, 60s
          const default429BackoffMs = [20000, 40000, 60000];
          const waitTime =
            suggestedDelaySec !== null
              ? Math.ceil((suggestedDelaySec + 1) * 1000)
              : (default429BackoffMs[rateLimitRetries - 1] ?? (rateLimitRetries * 20000));

          // 5. Log clear console message indicating 429 and wait duration
          console.log(
            `Gemini request failed (429). Retrying in ${waitTime / 1000} seconds...`
          );

          await new Promise(resolve => setTimeout(resolve, waitTime));

          continue;
        }

        // 4. Cap 429 retries at 3 attempts; do not fall through to JSON repair
        throw error;
      }

      // Check for temporary 503 or socket errors
      const is503 = error?.status === 503;
      const isSocket =
        error?.code === 'UND_ERR_SOCKET' ||
        error?.message === 'fetch failed' ||
        error?.cause?.code === 'UND_ERR_SOCKET';

      if (attempt < maxAttempts && (is503 || isSocket)) {
        const errorType = is503 ? '503' : 'socket';
        const waitTime = Math.min(attempt * 15000, 60000);

        console.log(
          `Gemini request failed (${errorType}). Retrying in ${waitTime / 1000} seconds...`
        );

        await new Promise(resolve => setTimeout(resolve, waitTime));

        continue;
      }

      if (attempt < maxAttempts) {
        repairNote =
          `\n\nYour previous output failed: ${error.message}. ` +
          `Fix the problem and return corrected JSON only.`;

        console.log(
          `LLM response validation failed. Retrying... (${attempt}/${maxAttempts})`
        );

        continue;
      }
    }
  }

  throw new Error(
    `LLM response remained invalid after ${maxAttempts} attempts: ${
      lastError?.message || 'unknown error'
    }`,
    { cause: lastError }
  );
}

function cleanProviderSchema(input) {
  if (Array.isArray(input)) {
    return input.map(cleanProviderSchema);
  }

  if (!input || typeof input !== 'object') {
    return input;
  }

  const unsupported = new Set([
    '$schema',
    '$id',
    'title',
    'minItems',
    'maxItems',
    'minLength',
    'maxLength',
  ]);

  return Object.fromEntries(
    Object.entries(input)
      .filter(([key]) => !unsupported.has(key))
      .map(([key, value]) => [key, cleanProviderSchema(value)])
  );
}
