import { proxyJson } from '@/lib/upstream';
import type { Lead, LeadUpdate } from '@/lib/types';

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = (await request.json()) as LeadUpdate;
  return proxyJson<Lead>(`/automation/leads/${encodeURIComponent(id)}`, { method: 'PATCH', body });
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<null>(`/automation/leads/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
