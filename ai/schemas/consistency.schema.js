import { z } from 'zod';

export const consistencySchema = z.object({
  is_consistent: z.boolean(),
  overall_score: z.number().min(0).max(10),
  issues: z.array(
    z.object({
      area: z.string(),
      description: z.string(),
      severity: z.enum(['minor', 'major']),
    })
  ),
  summary: z.string(),
});
