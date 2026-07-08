import { NextResponse } from 'next/server';
import { upstreamFetchRaw, UpstreamConfigError, UpstreamUnreachableError } from '@/lib/upstream';

export async function GET(request: Request) {
  try {
    const { search } = new URL(request.url);
    const upstreamRes = await upstreamFetchRaw(`/automation/export${search}`);

    if (!upstreamRes.ok) {
      const message = await upstreamRes.text();
      return NextResponse.json(
        { success: false, message: message || 'Export failed', data: null, error: true },
        { status: upstreamRes.status }
      );
    }

    return new NextResponse(upstreamRes.body, {
      status: 200,
      headers: {
        'Content-Type': upstreamRes.headers.get('Content-Type') ?? 'text/csv',
        'Content-Disposition': upstreamRes.headers.get('Content-Disposition') ?? 'attachment; filename="leads_export.csv"',
      },
    });
  } catch (err) {
    if (err instanceof UpstreamUnreachableError) {
      return NextResponse.json(
        { success: false, message: err.message, data: null, error: true, code: 'unreachable' },
        { status: 502 }
      );
    }
    if (err instanceof UpstreamConfigError) {
      return NextResponse.json(
        { success: false, message: err.message, data: null, error: true, code: 'config' },
        { status: 500 }
      );
    }
    throw err;
  }
}
