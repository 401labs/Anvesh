import { proxyJson } from '@/lib/upstream';
import type { OutreachLogsPage } from '@/lib/types';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  return proxyJson<OutreachLogsPage>(`/outreach/logs?${searchParams.toString()}`);
}
