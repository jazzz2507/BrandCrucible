import { z } from 'zod';

export const discoverSchema = z.object({
  audience: z.object({ primary: z.string(), secondary: z.string() }),
  problem_statement: z.string(),
  constraints: z.array(z.string()),
  assumptions: z.array(z.string()),
  open_questions: z.array(z.string()),
});
