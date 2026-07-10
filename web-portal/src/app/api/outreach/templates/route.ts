import { proxyJson } from '@/lib/upstream';
import type { EmailTemplate, EmailTemplateCreate, EmailTemplatesResponse } from '@/lib/types';

export async function GET() {
  return proxyJson<EmailTemplatesResponse>('/outreach/templates');
}

export async function POST(request: Request) {
  const body = (await request.json()) as EmailTemplateCreate;
  return proxyJson<EmailTemplate>('/outreach/templates', { method: 'POST', body });
}
