import { proxyJson } from '@/lib/upstream';
import type { Task } from '@/lib/types';

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<Task>(`/automation/tasks/${encodeURIComponent(id)}`);
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<null>(`/automation/tasks/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
