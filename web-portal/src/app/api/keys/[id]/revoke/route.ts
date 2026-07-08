import { proxyJson } from '@/lib/upstream';

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<null>(`/admin/keys/${encodeURIComponent(id)}/revoke`, { method: 'POST' });
}
