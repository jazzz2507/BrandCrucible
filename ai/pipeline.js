import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { discover } from './stages/discover.js';
import { position } from './stages/position.js';
import { shape } from './stages/shape.js';
import { visualize } from './stages/visualize.js';
import { deliver } from './stages/deliver.js';
import { consistencyCheck } from './stages/consistency-check.js';
import { challenge } from './challenger/challenge.js';
import { clearTraceLog, getTraceLog, logTraceEvent } from './trace/logger.js';

export async function runPipeline(idea) {
  clearTraceLog();

  const discovery = await discover(idea);
  logTraceEvent('Discover', idea, discovery);

  const positioning = await position(idea, { discovery });
  logTraceEvent('Position', { idea, discovery }, positioning);

  const verbalIdentity = await shape(idea, { discovery, positioning });
  logTraceEvent('Shape', { idea, discovery, positioning }, verbalIdentity);

  const visualIdentity = await visualize(idea, { discovery, positioning, verbalIdentity });
  logTraceEvent('Visualize', { idea, positioning, verbalIdentity }, visualIdentity);

  const candidates = [
    ...verbalIdentity.candidates.map((candidate) => ({ type: 'name', value: candidate.name, rationale: candidate.rationale, risk: candidate.risk })),
    ...verbalIdentity.tagline_options.map((tagline) => ({ type: 'tagline', value: tagline })),
  ];
  const challengeResult = await challenge(candidates, {
    value_proposition: positioning.value_proposition,
    differentiators: positioning.differentiators,
    positioning_statement: positioning.positioning_statement,
    audience: discovery.audience,
  }, async ({ type, value, feedback, attempt }) => {
    const revised = await shape(idea, {
      discovery,
      positioning,
      revision_feedback: `Replace this ${type}: “${value}”. Challenge feedback: ${feedback}. This is replacement attempt ${attempt}; produce a genuinely different option.`,
    });
    return type === 'name'
      ? { value: revised.candidates[0].name, rationale: revised.candidates[0].rationale, risk: revised.candidates[0].risk }
      : { value: revised.tagline_options[0] };
  });

  const rankByScore = (items) => [...items].sort((a, b) => {
    const isPassA = a.verdict === 'pass' ? 1 : 0;
    const isPassB = b.verdict === 'pass' ? 1 : 0;
    if (isPassA !== isPassB) return isPassB - isPassA;
    const mean = (scores) => scores ? Object.values(scores).reduce((sum, value) => sum + value, 0) / Object.values(scores).length : -1;
    return mean(b.score) - mean(a.score);
  });
  const chosenName = rankByScore(challengeResult.items.filter((item) => item.type === 'name'))[0] || candidates.find((item) => item.type === 'name');
  const chosenTagline = rankByScore(challengeResult.items.filter((item) => item.type === 'tagline'))[0] || candidates.find((item) => item.type === 'tagline');
  const brandKit = await deliver(idea, {
    discovery,
    positioning,
    verbal_identity: verbalIdentity,
    visual_identity: visualIdentity,
    chosen_name: chosenName?.value,
    chosen_tagline: chosenTagline?.value,
    challenge_history: challengeResult.history,
  });
  logTraceEvent('Deliver', { chosen_name: chosenName?.value, chosen_tagline: chosenTagline?.value }, brandKit);

  const consistencyResult = await consistencyCheck(brandKit, { idea });
  logTraceEvent('ConsistencyCheck', { brandKit }, consistencyResult, { score: consistencyResult.overall_score });

  return { brandKit, consistencyCheck: consistencyResult, trace: getTraceLog() };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('./test-ideas.json', import.meta.url), 'utf8'));
  const idea = process.argv[2] ? ideas[Number(process.argv[2]) - 1] : ideas[0];
  console.log(JSON.stringify(await runPipeline(idea), null, 2));
}
