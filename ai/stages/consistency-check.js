import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { callLLM } from '../llm.js';
import { consistencySchema } from '../schemas/consistency.schema.js';

const prompt = await readFile(new URL('../prompts/consistency.txt', import.meta.url), 'utf8');

// Consistency Check evaluates the overall coherence and alignment of the final brand kit.
export async function consistencyCheck(brandKit, previousStageOutputs = {}) {
  return callLLM(prompt, { brand_kit: brandKit, context: previousStageOutputs }, consistencySchema);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const raw = await readFile(new URL('../golden-run-output.json', import.meta.url));
  const isUtf16 = raw[0] === 0xff && raw[1] === 0xfe;
  const goldenRun = JSON.parse(raw.toString(isUtf16 ? 'utf16le' : 'utf8').replace(/^\uFEFF/, ''));
  console.log(JSON.stringify(await consistencyCheck(goldenRun.brandKit), null, 2));
}
