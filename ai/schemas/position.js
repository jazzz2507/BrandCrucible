import { z } from 'zod';

export const positionSchema = z.object({
  value_proposition: z.string(),
  differentiators: z.array(z.string()),
  competitive_angle: z.string(),
  positioning_statement: z.string(),
});
