import { z } from 'zod';

export const visualizeSchema = z.object({
  color_direction: z.string(),
  typography_direction: z.string(),
  imagery_direction: z.string(),
  rationale: z.string(),
});
