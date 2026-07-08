import { proxyJson } from '@/lib/upstream';

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<{ task_id: string }>(`/automation/tasks/${encodeURIComponent(id)}/stop`, { method: 'POST' });
}
