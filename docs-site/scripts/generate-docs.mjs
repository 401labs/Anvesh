import { generateFiles } from 'fumadocs-openapi';
import { createOpenAPI } from 'fumadocs-openapi/server';
import fs from 'fs';
import path from 'path';

// Use local openapi.json if available
const localSpecPath = path.resolve(process.cwd(), 'openapi.json');

// We use relative path so generated MDX uses relative path
const relativePath = './openapi.json'; 

let input = [];

if (fs.existsSync(localSpecPath)) {
  console.log(`📄 Found local OpenAPI spec at: ${localSpecPath}`);
  input = [relativePath]; 
} else {
  const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
  console.log(`📡 Fetching OpenAPI spec from: ${BACKEND_URL}/openapi.json`);
  input = [`${BACKEND_URL}/openapi.json`];
}

try {
  const openapi = createOpenAPI({ input });

  await generateFiles({
    input: openapi,
    output: './content/docs/api',
    groupBy: 'tag',
  });

  console.log('✅ API documentation generated successfully!');
  console.log('📁 Output: ./content/docs/api');
} catch (error) {
  console.error('❌ Failed to generate docs:', error.message);
  process.exit(1);
}
