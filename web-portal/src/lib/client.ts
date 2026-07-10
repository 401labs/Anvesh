'use client';

import type { ApiEnvelope } from './types';

/** Calls one of the portal's own /api/* routes and always resolves to an envelope, never throws. */
export async function apiRequest<T>(url: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  try {
    const res = await fetch(url, { cache: 'no-store', ...init });
    return (await res.json()) as ApiEnvelope<T>;
  } catch {
    return { success: false, message: 'Could not reach the portal server.', data: null, error: true };
  }
}

export function postJson<T>(url: string, body?: unknown) {
  return apiRequest<T>(url, {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function patchJson<T>(url: string, body?: unknown) {
  return apiRequest<T>(url, {
    method: 'PATCH',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function putJson<T>(url: string, body?: unknown) {
  return apiRequest<T>(url, {
    method: 'PUT',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function deleteJson<T>(url: string) {
  return apiRequest<T>(url, { method: 'DELETE' });
}
