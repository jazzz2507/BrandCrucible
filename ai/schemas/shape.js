import { z } from 'zod';

export const shapeSchema = z.object({
  candidates: z.array(z.object({ name: z.string(), rationale: z.string(), risk: z.string() })).min(1),
  personality_traits: z.array(z.string()),
  tagline_options: z.array(z.string()).min(1),
  voice_description: z.string(),
});
