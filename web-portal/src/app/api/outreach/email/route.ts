import { proxyJson } from '@/lib/upstream';
import type { SendEmailRequest, SendEmailResult } from '@/lib/types';

export async function POST(request: Request) {
  const body = (await request.json()) as SendEmailRequest;
  return proxyJson<SendEmailResult>('/outreach/email/send', { method: 'POST', body });
}
