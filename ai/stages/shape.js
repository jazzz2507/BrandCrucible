import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { shapeSchema } from '../schemas/shape.js';

const prompt = await readFile(new URL('../prompts/shape.txt', import.meta.url), 'utf8');
// Shape creates verbal identity options from the established positioning.
export async function shape(userInput, previousStageOutputs = {}) {
  const feedback = previousStageOutputs.revision_feedback;
  const taskPrompt = feedback ? `${prompt}\nRevision guidance for the replacement: ${feedback}` : prompt;
  return callLLM(taskPrompt, { idea: userInput, context: previousStageOutputs }, shapeSchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('../test-ideas.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(await shape(ideas[0]), null, 2));
}
