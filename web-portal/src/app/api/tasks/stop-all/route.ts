import { proxyJson } from '@/lib/upstream';

export async function POST() {
  return proxyJson<{ tasks_stopped: number }>('/automation/stop', { method: 'POST' });
}
