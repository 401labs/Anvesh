import { proxyJson } from '@/lib/upstream';
import type { Schedule, ScheduleCreate, SchedulesResponse } from '@/lib/types';

export async function GET() {
  return proxyJson<SchedulesResponse>('/schedules');
}

export async function POST(request: Request) {
  const body: ScheduleCreate = await request.json();
  return proxyJson<Schedule>('/schedules', { method: 'POST', body });
}
