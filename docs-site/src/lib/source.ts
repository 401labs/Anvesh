import { docs } from 'fumadocs-mdx:collections/server';
import { type InferPageType, loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/lucide-icons';
import { createOpenAPI } from 'fumadocs-openapi/server';
import path from 'path';
import fs from 'fs';

// OpenAPI server instance
export const openapi = createOpenAPI({
  // Map the relative path (used in MDX) to the actual content loaded from file, wrapped in function as required by type
  input: () => ({
    './openapi.json': JSON.parse(fs.readFileSync(path.join(process.cwd(), 'openapi.json'), 'utf-8'))
  }),
});

// See https://fumadocs.dev/docs/headless/source-api for more info
export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
  plugins: [lucideIconsPlugin()],
});

export function getPageImage(page: InferPageType<typeof source>) {
  const segments = [...page.slugs, 'image.png'];

  return {
    segments,
    url: `/og/docs/${segments.join('/')}`,
  };
}

export async function getLLMText(page: InferPageType<typeof source>) {
  const processed = await page.data.getText('processed');

  return `# ${page.data.title}

${processed}`;
}
