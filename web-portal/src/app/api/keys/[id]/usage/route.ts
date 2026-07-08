import { proxyJson } from '@/lib/upstream';
import type { UsageStats } from '@/lib/types';

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<UsageStats>(`/admin/keys/${encodeURIComponent(id)}/usage`);
}
