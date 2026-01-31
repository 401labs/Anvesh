# docs-site

This is a Next.js application generated with
[Create Fumadocs](https://github.com/fuma-nama/fumadocs).

## Quick Start

Run development server:

```bash
bun run dev
```

Open http://localhost:3000 with your browser to see the result.

## API Documentation

Generate API documentation from the FastAPI backend:

```bash
# Make sure the backend is running first:
cd ../automation-server && uv run uvicorn app.main:app --reload

# Then generate the docs (in this directory):
bun run generate:docs
```

This fetches the OpenAPI spec from `http://localhost:8000/openapi.json` and generates MDX files in `content/docs/api/`.

## Explore

In the project, you can see:

- `lib/source.ts`: Code for content source adapter, [`loader()`](https://fumadocs.dev/docs/headless/source-api) provides the interface to access your content.
- `lib/layout.shared.tsx`: Shared options for layouts, optional but preferred to keep.
- `scripts/generate-docs.mjs`: Script to generate API docs from OpenAPI spec.

| Route                     | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `app/(home)`              | The route group for your landing page and other pages. |
| `app/docs`                | The documentation layout and pages.                    |
| `app/api/search/route.ts` | The Route Handler for search.                          |

### Fumadocs MDX

A `source.config.ts` config file has been included, you can customise different options like frontmatter schema.

Read the [Introduction](https://fumadocs.dev/docs/mdx) for further details.

## Learn More

To learn more about Next.js and Fumadocs, take a look at the following
resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js
  features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.
- [Fumadocs](https://fumadocs.dev) - learn about Fumadocs

## 🚀 CI/CD

This project uses GitHub Actions for automated testing and deployment.
- **Build & Lint**: Runs on every push to `main` and PRs affecting `docs-site/**`.
- **Workflow**: `.github/workflows/docs-build.yml`
