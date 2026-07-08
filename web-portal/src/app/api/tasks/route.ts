import { proxyJson } from '@/lib/upstream';
import type { TasksPage, TaskConfig } from '@/lib/types';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get('limit') ?? '20';
  const offset = searchParams.get('offset') ?? '0';
  return proxyJson<TasksPage>(`/automation/tasks?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`);
}

export async function POST(request: Request) {
  const body = (await request.json()) as TaskConfig;
  return proxyJson<{ task_id: string }>('/automation/start', { method: 'POST', body });
}
