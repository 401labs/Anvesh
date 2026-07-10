import { proxyJson } from '@/lib/upstream';
import type { EmailConfig, EmailConfigUpdate } from '@/lib/types';

export async function GET() {
  return proxyJson<EmailConfig>('/config/email');
}

export async function PUT(request: Request) {
  const body: EmailConfigUpdate = await request.json();
  return proxyJson<EmailConfig>('/config/email', { method: 'PUT', body });
}
