# AI Pipeline Handoff Documentation

This document contains the complete technical specification for porting the Brand Crucible AI pipeline from Node.js into a Python FastAPI backend. All prompts and schemas are copied verbatim from the source repository.

---

## Table of Contents

1. [Pipeline Overview & Execution Flow](#1-pipeline-overview--execution-flow)
2. [Stage Prompts & Schemas (7 Stages)](#2-stage-prompts--schemas-7-stages)
   - [Stage 1: Discover](#stage-1-discover)
   - [Stage 2: Position](#stage-2-position)
   - [Stage 3: Shape](#stage-3-shape)
   - [Stage 4: Visualize](#stage-4-visualize)
   - [Stage 5: Challenge](#stage-5-challenge)
   - [Stage 6: Deliver](#stage-6-deliver)
   - [Stage 7: Consistency Check](#stage-7-consistency-check)
3. [Challenger Logic](#3-challenger-logic)
4. [Consistency Check Logic](#4-consistency-check-logic)
5. [Selection & Ranking Logic](#5-selection--ranking-logic)
6. [LLM Adapter & Retry Strategy](#6-llm-adapter--retry-strategy)
7. [Python FastAPI Porting Recommendations](#7-python-fastapi-porting-recommendations)

---

## 1. Pipeline Overview & Execution Flow

The pipeline executes sequentially in the following order:

```
[User Idea]
    │
    ▼
1. Discover ──────────► (audience, problem_statement, constraints, assumptions, open_questions)
    │
    ▼
2. Position ──────────► (value_proposition, differentiators, competitive_angle, positioning_statement)
    │
    ▼
3. Shape ─────────────► (candidates [name, rationale, risk], personality_traits, tagline_options, voice_description)
    │
    ▼
4. Visualize ─────────► (color_direction, typography_direction, imagery_direction, rationale)
    │
    ▼
5. Challenge Loop ────► (evaluates each name & tagline candidate independently with up to 2 revisions)
    │
    ▼
[Candidate Ranking] ──► (selects best name & tagline by verdict priority then mean score)
    │
    ▼
6. Deliver ───────────► (compiles final brandKit: discovery + positioning + shape + visual + chosen name/tagline)
    │
    ▼
7. Consistency Check ─► (evaluates final brand kit against initial idea & strategy; assigns score & flags issues)
    │
    ▼
[Return { brandKit, consistencyCheck, trace }]
```

---

## 2. Stage Prompts & Schemas (7 Stages)

### Stage 1: Discover

#### Exact System Prompt (`prompts/discover.txt`)
```text
You are the Discover agent. Identify the startup idea's likely primary and secondary audiences, the core problem, constraints, assumptions, and unanswered questions. This stage is research framing only: do not propose names, taglines, brand voice, positioning, or visual identity. Be specific to the supplied idea and distinguish known facts from assumptions. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/discover.js`)
```javascript
import { z } from 'zod';

export const discoverSchema = z.object({
  audience: z.object({ primary: z.string(), secondary: z.string() }),
  problem_statement: z.string(),
  constraints: z.array(z.string()),
  assumptions: z.array(z.string()),
  open_questions: z.array(z.string()),
});
```

---

### Stage 2: Position

#### Exact System Prompt (`prompts/position.txt`)
```text
You are the Position agent. Define a clear value proposition, differentiators, competitive angle, and positioning statement using the idea and discovery context. This stage is strategic positioning only: do not generate names, taglines, personality, voice, or visual directions. Be specific to this idea and audience, avoiding generic claims. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/position.js`)
```javascript
import { z } from 'zod';

export const positionSchema = z.object({
  value_proposition: z.string(),
  differentiators: z.array(z.string()),
  competitive_angle: z.string(),
  positioning_statement: z.string(),
});
```

---

### Stage 3: Shape

#### Exact System Prompt (`prompts/shape.txt`)
```text
You are the Shape agent. Create candidate brand names with rationale and risk, personality traits, tagline options, and a concise voice description using the positioning context. This stage handles verbal identity only: do not revisit discovery, rewrite positioning, or suggest colors, typography, or imagery. Make ideas memorable and specific to this startup, not generic. If revision guidance is supplied, address it directly. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/shape.js`)
```javascript
import { z } from 'zod';

export const shapeSchema = z.object({
  candidates: z.array(z.object({ name: z.string(), rationale: z.string(), risk: z.string() })).min(1),
  personality_traits: z.array(z.string()),
  tagline_options: z.array(z.string()).min(1),
  voice_description: z.string(),
});
```

---

### Stage 4: Visualize

#### Exact System Prompt (`prompts/visualize.txt`)
```text
You are the Visualize agent. Propose a cohesive color, typography, and imagery direction, with rationale grounded in the brand strategy and personality. This stage is visual direction only: do not invent names, taglines, or revise the positioning. Be concrete and specific to this brand rather than relying on generic design adjectives. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/visualize.js`)
```javascript
import { z } from 'zod';

export const visualizeSchema = z.object({
  color_direction: z.string(),
  typography_direction: z.string(),
  imagery_direction: z.string(),
  rationale: z.string(),
});
```

---

### Stage 5: Challenge

#### Exact System Prompt (`prompts/challenge.txt`)
```text
You are the Challenge agent. Critically assess one supplied brand item against its positioning context. Score cliche risk, distinctiveness, audience fit, and consistency with positioning from 0 to 10; for cliche risk, a higher score means lower risk / more original. Give actionable feedback and a pass, revise, or reject verdict. Do not generate a replacement or change the strategy. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/challenge.js`)
```javascript
import { z } from 'zod';

const score = z.number().min(0).max(10);
export const challengeSchema = z.object({
  item: z.string(),
  scores: z.object({
    cliche_risk: score,
    distinctiveness: score,
    audience_fit: score,
    consistency_with_positioning: score,
  }),
  verdict: z.enum(['pass', 'revise', 'reject']),
  feedback: z.string(),
});
```

---

### Stage 6: Deliver

#### Exact System Prompt (`prompts/deliver.txt`)
```text
You are the Deliver agent. Compile the validated prior-stage decisions into one clean, exportable brand kit using the supplied chosen name, tagline, discovery, positioning, verbal identity, and visual direction. This stage compiles only: do not invent missing strategy or add new creative directions. Keep every field specific and faithful to supplied outputs. Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/deliver.js`)
```javascript
import { z } from 'zod';

export const deliverSchema = z.object({
  brand_name: z.string(),
  tagline: z.string(),
  discovery: z.object({ audience: z.object({ primary: z.string(), secondary: z.string() }), problem_statement: z.string(), constraints: z.array(z.string()), assumptions: z.array(z.string()), open_questions: z.array(z.string()) }),
  positioning: z.object({ value_proposition: z.string(), differentiators: z.array(z.string()), competitive_angle: z.string(), positioning_statement: z.string() }),
  brand_shape: z.object({ personality_traits: z.array(z.string()), voice_description: z.string() }),
  visual_identity: z.object({ color_direction: z.string(), typography_direction: z.string(), imagery_direction: z.string(), rationale: z.string() }),
  rationale: z.string(),
});
```

---

### Stage 7: Consistency Check

#### Exact System Prompt (`prompts/consistency.txt`)
```text
You are the Consistency Check agent. Critically evaluate the final compiled brand kit as a whole against the original idea and prior stage decisions. Check specifically:
1. Does the final brand name match the original idea?
2. Does the tagline directly support the positioning?
3. Do the brand personality traits match the discovered audience and problem?
4. Does the visual identity fit the brand personality and positioning?
5. Is there overall coherence across name, tagline, positioning, voice, and visual identity?
6. Has the brand drifted from the core problem and audience of the original idea?

Evaluate issues (if any) with area, description, and severity ("minor" | "major"). Provide an overall_score from 0 to 10, a boolean is_consistent (true if score >= 7 and no unaddressed major disconnects), and a concise summary (one or two sentences). Return ONLY valid JSON matching the provided schema, with no preamble or markdown fences.
```

#### Exact Zod Schema (`schemas/consistency.schema.js`)
```javascript
import { z } from 'zod';

export const consistencySchema = z.object({
  is_consistent: z.boolean(),
  overall_score: z.number().min(0).max(10),
  issues: z.array(
    z.object({
      area: z.string(),
      description: z.string(),
      severity: z.enum(['minor', 'major']),
    })
  ),
  summary: z.string(),
});
```

---

## 3. Challenger Logic

Implemented in `ai/challenger/challenge.js`.

### 1. Scoring Dimensions and Scale
The Challenger assesses candidates across 4 dimensions on a **0 to 10** numeric scale:
- `cliche_risk`: **Higher score = lower risk / more original.**
- `distinctiveness`: Uniqueness and memorability against competitors.
- `audience_fit`: Resonance with discovered target audience.
- `consistency_with_positioning`: Alignment with the strategic positioning statement and value proposition.

### 2. Pass / Revise / Reject Criteria (`needsRevision`)
The LLM returns an initial verdict (`pass`, `revise`, or `reject`). The code applies a strict programmatic gatekeeper rule:

```javascript
function average(scores) {
  return scoreKeys.reduce((sum, key) => sum + scores[key], 0) / scoreKeys.length;
}

function needsRevision(result) {
  return average(result.scores) < 6 || scoreKeys.some((key) => result.scores[key] < 4) || result.verdict !== 'pass';
}
```

An item **requires revision** if ANY of the following conditions are met:
1. The **average** of the 4 score dimensions is `< 6.0`.
2. **Any individual dimension** score is `< 4.0`.
3. The LLM's returned verdict is **not** `'pass'` (i.e. `'revise'` or `'reject'`).

If `needsRevision(result)` is `false`, the candidate passes immediately and the loop breaks early.

### 3. Revision Count and Exhaustion Behavior
- `MAX_REVISIONS = 2` (up to 3 total attempts: attempt `0` initial, attempt `1` first revision, attempt `2` second revision).
- The challenger tracks the `best` candidate across all attempts based on highest average score (`average(result.scores)`).
- When an item needs revision and `revision < MAX_REVISIONS`:
  - It invokes `generateReplacement({ ...current, feedback: result.feedback, attempt: revision + 1 })` which calls the `Shape` stage with targeted revision instructions.
- **When revisions are exhausted** (`revision === MAX_REVISIONS` or no replacement produced):
  - The loop terminates.
  - The candidate with the highest average score seen (`best`) is selected.
  - Its final verdict is assigned as: `needsRevision(best.result) ? 'revise' : 'pass'`.
  - The item is flagged with `exhausted_revisions: true` if `needsRevision(best.result) && itemHistory.length > 1 && itemHistory.length === MAX_REVISIONS + 1`.
  - The complete history of all attempts is recorded in `challengeResult.history`.

### 4. Inter-Call Delay (`CALL_DELAY_MS`)
- Exact value: **`CALL_DELAY_MS = 4500`** (4.5 seconds / 4500ms).
- **Why it exists**: Gemini API rate-limiting guard. During the challenger stage, evaluating multiple names and taglines with up to 2 revisions each can trigger 10+ LLM calls in quick succession. The 4500ms delay prevents bursting past RPM limits and avoids 429 `RESOURCE_EXHAUSTED` errors.

---

## 4. Consistency Check Logic

Implemented in `ai/stages/consistency-check.js` and called in `ai/pipeline.js`.

### 1. Placement in the Pipeline
- Runs **after** the `Deliver` stage has compiled the full `brandKit`.
- Evaluates `{ brand_kit: brandKit, context: { idea } }`.
- Runs **before** returning the final pipeline response.

### 2. What It Checks
It performs a holistic end-to-end evaluation checking:
1. **Name Alignment**: Does the final brand name match the original idea and concept?
2. **Tagline Support**: Does the tagline directly support the strategic positioning?
3. **Personality Fit**: Do brand personality traits match the audience and problem?
4. **Visual Cohesion**: Does the visual identity (color, typography, imagery) fit the personality and positioning?
5. **Holistic Coherence**: Is there unified consistency across name, tagline, positioning, voice, and visual identity?
6. **Drift Detection**: Has the brand drifted from the core problem and audience of the original startup idea?

### 3. Schema Fields Meaning
- `is_consistent` (`boolean`): True if `overall_score >= 7` and there are no unaddressed major disconnects.
- `overall_score` (`number`, 0-10): Quantitative alignment rating.
- `issues` (`array` of objects):
  - `area` (`string`): The stage or element where the issue occurred (e.g., `'visual_identity'`, `'tagline'`, `'audience'`).
  - `description` (`string`): Specific details of what is inconsistent or drifted.
  - `severity` (`'minor' | 'major'`): Severity classification.
- `summary` (`string`): 1-2 sentence executive evaluation summary.

---

## 5. Selection & Ranking Logic

Implemented in `ai/pipeline.js`.

After the challenge stage evaluates all name and tagline candidates, the pipeline ranks the candidates to select the top `chosenName` and `chosenTagline`.

### Ranking Rules
1. **Verdict Priority**: Candidates with `verdict === 'pass'` (`isPass === 1`) always rank higher than non-pass candidates (`isPass === 0`).
2. **Mean Score**: For candidates with the same verdict status, rank by descending arithmetic mean of all 4 score dimensions (`mean(b.score) - mean(a.score)`).
3. **Fallback**: If ranking returns empty, fallback to the first candidate from the original shape list.

### Exact Implementation Code (`pipeline.js`)
```javascript
const rankByScore = (items) => [...items].sort((a, b) => {
  const isPassA = a.verdict === 'pass' ? 1 : 0;
  const isPassB = b.verdict === 'pass' ? 1 : 0;
  if (isPassA !== isPassB) return isPassB - isPassA;
  const mean = (scores) => scores ? Object.values(scores).reduce((sum, value) => sum + value, 0) / Object.values(scores).length : -1;
  return mean(b.score) - mean(a.score);
});

const chosenName = rankByScore(challengeResult.items.filter((item) => item.type === 'name'))[0] || candidates.find((item) => item.type === 'name');
const chosenTagline = rankByScore(challengeResult.items.filter((item) => item.type === 'tagline'))[0] || candidates.find((item) => item.type === 'tagline');
```

---

## 6. LLM Adapter & Retry Strategy

Implemented in `ai/llm.js`.

### 1. Retry Strategy for 503 and Socket Errors
- **Triggers**: HTTP status `503`, socket errors (`UND_ERR_SOCKET`), or network fetch failures (`fetch failed`).
- **Attempts**: Participates in the overall `maxAttempts = 8` loop.
- **Backoff calculation**:
  ```javascript
  const waitTime = Math.min(attempt * 15000, 60000); // 15s, 30s, 45s, 60s cap
  ```
- **Behavior**: Waits `waitTime` and retries the exact same request.

### 2. Retry Strategy for 429 Rate-Limit Errors
- **Trigger**: HTTP status `429` / `RESOURCE_EXHAUSTED`.
- **Max 429 Retries**: Dedicated cap `max429Retries = 3` (independent of general schema errors).
- **Suggested Delay Extraction (`extractRetryDelay`)**:
  - Checks `err.errorDetails` and `err.details` for `retryDelay`, `retry_delay`, `metadata.retryDelay`, and `metadata['retry-delay']`.
  - Supports numeric values, seconds/nanos objects (`{ seconds, nanos }`), and string formats (e.g., `"12.5s"`).
  - Also inspects `err.message` with regex:
    - `/(?:retryDelay|retry_delay)["']?\s*[:=]\s*["']?([0-9.]+)\s*s?/i`
    - `/(?:retry|wait)\s+(?:in|after)\s+([0-9.]+)\s*(?:s|seconds)?/i`
- **Wait Duration Calculation**:
  - If a suggested delay is found: `Math.ceil((suggestedDelaySec + 1) * 1000)` ms (adds a 1-second safety buffer).
  - If no delay is suggested, fallback to tiered backoff: `[20000, 40000, 60000]` ms (20s, 40s, 60s).
- **Cap Behavior**: If 429 retries exceed 3, the error is immediately thrown (it does NOT fall through to the JSON prompt repair loop).

### 3. Schema Validation & Repair Loop
- When JSON parsing or schema validation fails, the adapter increments `attempt` and appends a dynamic repair note to the next prompt:
  ```text
  \n\nYour previous output failed: ${error.message}. Fix the problem and return corrected JSON only.
  ```
- Up to `maxAttempts = 8` attempts are made before throwing a terminal error.

### 4. Schema Sanitization (`cleanProviderSchema`)
Gemini's structured outputs API rejects certain standard JSON schema keywords. The adapter strips:
- `$schema`, `$id`, `title`, `minItems`, `maxItems`, `minLength`, `maxLength`.

---

## 7. Python FastAPI Porting Recommendations

When porting this adapter and pipeline into Python with FastAPI:

1. **SDK Selection**:
   - The Node implementation uses `@google/genai` (Gemini 2.x / 3.x Flash SDK).
   - In Python, use `google-genai` (the new unified Google GenAI SDK: `pip install google-genai`) or `google-generativeai`.
2. **Schema Definition**:
   - Replace Zod schemas with **Pydantic v2 `BaseModel`** classes.
   - Pass models directly to `types.GenerateContentConfig(response_mime_type="application/json", response_schema=YourModel)`.
3. **Equivalence in Retry Handling**:
   - **429 Handling**: Catch `google.genai.errors.APIError` or `google.api_core.exceptions.ResourceExhausted`. Extract `retry_delay` from error metadata or apply `[20, 40, 60]` seconds backoff (max 3 retries).
   - **503 / Network Handling**: Catch `google.api_core.exceptions.ServiceUnavailable` and connection errors, backing off with `min(attempt * 15, 60)` seconds.
   - **Validation Loop**: Catch `pydantic.ValidationError` or JSON decoding errors and append the error message repair note up to 8 total attempts.
4. **Rate Limit Throttling**:
   - Maintain the `4.5s` delay (`asyncio.sleep(4.5)`) between challenger iterations to prevent RPM limits.
