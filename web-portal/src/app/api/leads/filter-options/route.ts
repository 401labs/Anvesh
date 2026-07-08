import { proxyJson } from '@/lib/upstream';
import type { LeadFilterOptions } from '@/lib/types';

export async function GET() {
  return proxyJson<LeadFilterOptions>('/automation/leads/filter-options');
}
