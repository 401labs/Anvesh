// Server-only helper for calling automation-server. Import this ONLY from
// route handlers (src/app/api/**/route.ts) — never from client components —
// so ADMIN_SECRET never ends up in the browser bundle.
import { NextResponse } from 'next/server';
import type { ApiEnvelope } from './types';

export class UpstreamConfigError extends Error {}
export class UpstreamUnreachableError extends Error {}

function baseUrl(): string {
  return process.env.AUTOMATION_API_URL ?? 'http://localhost:8000';
}

function authHeaders(): Record<string, string> {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) {
    throw new UpstreamConfigError('ADMIN_SECRET is not set — see web-portal/.env.local.example');
  }
  // X-Admin-Secret satisfies both admin-only routes and get_api_key's admin bypass
  // (see automation-server/app/middleware/auth.py) — the portal never needs a
  // separately-generated API key.
  return { 'X-Admin-Secret': secret };
}

async function doFetch(path: string, opts: { method?: string; body?: unknown }): Promise<Response> {
  const headers: Record<string, string> = { ...authHeaders() };
  let body: string | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  try {
    return await fetch(`${baseUrl()}${path}`, {
      method: opts.method ?? 'GET',
      headers,
      body,
      cache: 'no-store',
    });
  } catch {
    throw new UpstreamUnreachableError(`automation-server unreachable at ${baseUrl()}`);
  }
}

/** Call an automation-server JSON endpoint and return its status + parsed envelope, unchanged. */
export async function upstreamFetch<T>(
  path: string,
  opts: { method?: string; body?: unknown } = {}
): Promise<{ status: number; envelope: ApiEnvelope<T> }> {
  const res = await doFetch(path, opts);
  const envelope = (await res.json()) as ApiEnvelope<T>;
  return { status: res.status, envelope };
}

/** Call an automation-server endpoint that returns a raw body (e.g. CSV export) instead of the JSON envelope. */
export async function upstreamFetchRaw(path: string, opts: { method?: string } = {}): Promise<Response> {
  return doFetch(path, opts);
}

/**
 * Wraps a JSON route handler: calls automation-server, forwards its status/envelope
 * unchanged on success, and turns config/connectivity failures into a distinct
 * `code` the client can use to show a persistent "backend unreachable" banner
 * rather than a one-off error toast.
 */
export async function proxyJson<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<NextResponse> {
  try {
    const { status, envelope } = await upstreamFetch<T>(path, opts);
    return NextResponse.json(envelope, { status });
  } catch (err) {
    if (err instanceof UpstreamUnreachableError) {
      return NextResponse.json(
        { success: false, message: err.message, data: null, error: true, code: 'unreachable' } satisfies ApiEnvelope<null>,
        { status: 502 }
      );
    }
    if (err instanceof UpstreamConfigError) {
      return NextResponse.json(
        { success: false, message: err.message, data: null, error: true, code: 'config' } satisfies ApiEnvelope<null>,
        { status: 500 }
      );
    }
    throw err;
  }
}
