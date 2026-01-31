import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { MDXComponents } from 'mdx/types';
import { createAPIPage } from 'fumadocs-openapi/ui';
import { openapi } from '@/lib/source';

// Create the APIPage component using the OpenAPI server instance
const APIPage = createAPIPage(openapi);

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    APIPage,
    ...components,
  };
}
