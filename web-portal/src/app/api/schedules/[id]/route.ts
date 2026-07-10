import { proxyJson } from '@/lib/upstream';
import type { Schedule, ScheduleUpdate } from '@/lib/types';

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body: ScheduleUpdate = await request.json();
  return proxyJson<Schedule>(`/schedules/${encodeURIComponent(id)}`, { method: 'PATCH', body });
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson(`/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
