import { readFile } from 'node:fs/promises';
import { callLLM } from '../llm.js';
import { challengeSchema } from '../schemas/challenge.js';
import { logTraceEvent } from '../trace/logger.js';

const prompt = await readFile(new URL('../prompts/challenge.txt', import.meta.url), 'utf8');
const MAX_REVISIONS = 2;
const scoreKeys = ['cliche_risk', 'distinctiveness', 'audience_fit', 'consistency_with_positioning'];
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const CALL_DELAY_MS = 4500;

function average(scores) {
  return scoreKeys.reduce((sum, key) => sum + scores[key], 0) / scoreKeys.length;
}

function needsRevision(result) {
  return average(result.scores) < 6 || scoreKeys.some((key) => result.scores[key] < 4) || result.verdict !== 'pass';
}

// Challenge reviews each name/tagline independently and keeps a visible audit trail.
export async function challenge(items, positioningContext, generateReplacement = async () => null) {
  const acceptedItems = [];
  const history = [];

  for (const original of items) {
    let current = { ...original };
    let best = null;
    const itemHistory = [];

    for (let revision = 0; revision <= MAX_REVISIONS; revision += 1) {
      await delay(CALL_DELAY_MS);
      const result = await callLLM(prompt, {
        candidate: current,
        positioning_context: positioningContext,
        scoring_guidance: 'A high cliche_risk score means low risk and originality.',
      }, challengeSchema);
      const entry = { candidate: current, result, revision };
      itemHistory.push(entry);
      if (!best || average(result.scores) > average(best.result.scores)) best = entry;
      logTraceEvent('Challenge', current, result, { score: result.scores, revision, candidate_type: current.type });

      if (!needsRevision(result)) {
        best = entry;
        break;
      }
      if (revision === MAX_REVISIONS) break;

      await delay(CALL_DELAY_MS);
      const replacement = await generateReplacement({
        ...current,
        feedback: result.feedback,
        attempt: revision + 1,
      });
      if (!replacement) break;
      current = { ...current, ...replacement, value: replacement.value ?? replacement.name ?? replacement.tagline ?? replacement };
    }

    const exhausted = needsRevision(best.result) && itemHistory.length > 1 && itemHistory.length === MAX_REVISIONS + 1;
    const accepted = {
      ...best.candidate,
      value: best.candidate.value,
      score: best.result.scores,
      verdict: needsRevision(best.result) ? 'revise' : 'pass',
      feedback: best.result.feedback,
    };
    acceptedItems.push(accepted);
    history.push({ original, selected: accepted, exhausted_revisions: exhausted, attempts: itemHistory });
    if (exhausted) logTraceEvent('Challenge', original, accepted, { exhausted_revisions: true, attempts: itemHistory.length });
  }

  return { items: acceptedItems, history };
}