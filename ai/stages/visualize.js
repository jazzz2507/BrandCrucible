import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { visualizeSchema } from '../schemas/visualize.js';

const prompt = await readFile(new URL('../prompts/visualize.txt', import.meta.url), 'utf8');
// Visualize translates the strategy and verbal identity into visual direction.
export async function visualize(userInput, previousStageOutputs = {}) {
  return callLLM(prompt, { idea: userInput, context: previousStageOutputs }, visualizeSchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('../test-ideas.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(await visualize(ideas[0]), null, 2));
}
