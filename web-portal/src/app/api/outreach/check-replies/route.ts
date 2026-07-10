import { proxyJson } from '@/lib/upstream';

export async function POST() {
  return proxyJson<{ matched: number }>('/outreach/check-replies', { method: 'POST' });
}
