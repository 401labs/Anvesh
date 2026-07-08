import { proxyJson } from '@/lib/upstream';
import type { Lead, LeadCreate, LeadsPage } from '@/lib/types';

export async function GET(request: Request) {
  // Forward the query string as-is (limit/offset/filters/sort) — automation-server validates it.
  const { search } = new URL(request.url);
  return proxyJson<LeadsPage>(`/automation/leads${search}`);
}

export async function POST(request: Request) {
  const body = (await request.json()) as LeadCreate;
  return proxyJson<Lead>('/automation/leads', { method: 'POST', body });
}
