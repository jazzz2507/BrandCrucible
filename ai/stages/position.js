import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { positionSchema } from '../schemas/position.js';

const prompt = await readFile(new URL('../prompts/position.txt', import.meta.url), 'utf8');
// Position turns discovery into a clear strategic place in the market.
export async function position(userInput, previousStageOutputs = {}) {
  return callLLM(prompt, { idea: userInput, context: previousStageOutputs }, positionSchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('../test-ideas.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(await position(ideas[0]), null, 2));
}
