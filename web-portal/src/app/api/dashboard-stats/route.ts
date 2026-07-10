import { proxyJson } from '@/lib/upstream';
import type { DashboardStats } from '@/lib/types';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.toString();
  return proxyJson<DashboardStats>(`/stats${query ? `?${query}` : ''}`);
}
