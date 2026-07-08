import { proxyJson } from '@/lib/upstream';
import type { AutomationStats } from '@/lib/types';

export async function GET() {
  return proxyJson<AutomationStats>('/admin/automation/stats');
}
