import { proxyJson } from '@/lib/upstream';
import type { EmailTemplate, EmailTemplateUpdate } from '@/lib/types';

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = (await request.json()) as EmailTemplateUpdate;
  return proxyJson<EmailTemplate>(`/outreach/templates/${encodeURIComponent(id)}`, { method: 'PATCH', body });
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson<null>(`/outreach/templates/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
