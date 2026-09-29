import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { deliverSchema } from '../schemas/deliver.js';

const prompt = await readFile(new URL('../prompts/deliver.txt', import.meta.url), 'utf8');
// Deliver compiles approved stage outputs into the exportable brand kit.
export async function deliver(userInput, previousStageOutputs = {}) {
  return callLLM(prompt, { idea: userInput, context: previousStageOutputs }, deliverSchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const ideas = JSON.parse(await readFile(new URL('../test-ideas.json', import.meta.url), 'utf8'));
  console.log(JSON.stringify(await deliver(ideas[0], {}), null, 2));
}
