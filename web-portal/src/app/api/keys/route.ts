import { proxyJson } from '@/lib/upstream';
import type { ApiKeysPage, ApiKeyCreated, ApiKeyTier } from '@/lib/types';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get('limit') ?? '20';
  const offset = searchParams.get('offset') ?? '0';
  return proxyJson<ApiKeysPage>(`/admin/keys?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`);
}

export async function POST(request: Request) {
  const body = (await request.json()) as { name: string; tier: ApiKeyTier; expires_in_days?: number };
  return proxyJson<ApiKeyCreated>('/admin/keys', { method: 'POST', body });
}
