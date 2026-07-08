import { proxyJson } from '@/lib/upstream';

export async function POST(request: Request) {
  const body = (await request.json()) as { ids: number[] };
  return proxyJson<{ deleted: number }>('/automation/leads/bulk-delete', { method: 'POST', body });
}
