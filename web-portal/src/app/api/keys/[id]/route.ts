import { proxyJson } from '@/lib/upstream';
import type { ApiKey, ApiKeyUpdate } from '@/lib/types';

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<ApiKey>(`/admin/keys/${encodeURIComponent(id)}`);
}

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = (await request.json()) as ApiKeyUpdate;
  return proxyJson<ApiKey>(`/admin/keys/${encodeURIComponent(id)}`, { method: 'PATCH', body });
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<null>(`/admin/keys/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
