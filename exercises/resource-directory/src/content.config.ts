import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";
import { RESOURCE_CATEGORIES } from "./lib/resource-model";

// [Implementation 1]
// Invalid metadata stops the build before a route can publish incomplete content.
const resources = defineCollection({
  // [Implementation 1-1]
  // File names become stable entry ids; moving copy into Markdown does not add runtime fetching.
  loader: glob({
    base: "./src/content/resources",
    pattern: "**/*.md"
  }),
  schema: z.object({
    title: z.string().trim().min(1).max(80),
    summary: z.string().trim().min(1).max(180),
    category: z.enum(RESOURCE_CATEGORIES),
    tags: z.array(z.string().trim().min(1).max(24)).min(1).max(6),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
    featured: z.boolean().default(false),
    draft: z.boolean().default(false),
    sourceUrl: z.string().url().optional()
  })
});

export const collections = { resources };
