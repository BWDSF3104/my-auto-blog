import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(),
    pubDate: z.string(),
    description: z.string(),
    author: z.string().optional(),
    tags: z.array(z.string()).optional(),
    image: z.string().optional(),
  }).passthrough(),
  loader: glob({ pattern: '**/*.md', base: 'src/content/posts' }),
});

export const collections = { posts };
