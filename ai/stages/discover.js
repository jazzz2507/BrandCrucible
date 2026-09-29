import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { discoverSchema } from '../schemas/discover.js';

const prompt = await readFile(new URL('../prompts/discover.txt', import.meta.url), 'utf8');
// Discover frames the audience and problem before any brand creative begins.
export async function discover(userInput, previousStageOutputs = {}) {
  return callLLM(prompt, { idea: userInput, context: previousStageOutputs }, discoverSchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('../test-ideas.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(await discover(ideas[0]), null, 2));
}
