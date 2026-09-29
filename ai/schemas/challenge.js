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
