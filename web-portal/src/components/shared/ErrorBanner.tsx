import { AlertTriangle } from 'lucide-react';

interface ErrorBannerProps {
  message?: string;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div className="mb-6 flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/[0.06] px-4 py-3 text-sm text-amber-200">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        {message ?? 'automation-server is unreachable.'} Check that it&apos;s running and that{' '}
        <code className="rounded bg-black/20 px-1 py-0.5">web-portal/.env.local</code> is configured correctly.
      </span>
    </div>
  );
}
