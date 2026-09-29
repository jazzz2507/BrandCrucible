import { z } from 'zod';

export const deliverSchema = z.object({
  brand_name: z.string(),
  tagline: z.string(),
  discovery: z.object({ audience: z.object({ primary: z.string(), secondary: z.string() }), problem_statement: z.string(), constraints: z.array(z.string()), assumptions: z.array(z.string()), open_questions: z.array(z.string()) }),
  positioning: z.object({ value_proposition: z.string(), differentiators: z.array(z.string()), competitive_angle: z.string(), positioning_statement: z.string() }),
  brand_shape: z.object({ personality_traits: z.array(z.string()), voice_description: z.string() }),
  visual_identity: z.object({ color_direction: z.string(), typography_direction: z.string(), imagery_direction: z.string(), rationale: z.string() }),
  rationale: z.string(),
});
