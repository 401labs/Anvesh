'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { usePolling } from '@/hooks/usePolling';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { putJson } from '@/lib/client';
import type { EmailConfig, EmailConfigUpdate } from '@/lib/types';

export default function SettingsPage() {
  const { data, message, loading, unreachable, refetch } = usePolling<EmailConfig>('/api/config/email');
  const [values, setValues] = useState<EmailConfigUpdate>({});
  const [appPassword, setAppPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) {
      setValues({
        smtp_host: data.smtp_host,
        smtp_port: data.smtp_port,
        smtp_user: data.smtp_user,
        smtp_from_name: data.smtp_from_name,
        imap_host: data.imap_host,
        imap_port: data.imap_port,
      });
    }
  }, [data]);

  function set<K extends keyof EmailConfigUpdate>(key: K, value: EmailConfigUpdate[K]) {
    setValues((v) => ({ ...v, [key]: value }));
    setSaved(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const body: EmailConfigUpdate = { ...values };
    if (appPassword.trim()) {
      body.smtp_app_password = appPassword.trim();
    }

    const envelope = await putJson('/api/config/email', body);
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    setAppPassword('');
    setSaved(true);
    refetch();
  }

  return (
    <div className="w-full px-6 py-8 md:px-10">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight text-white">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          SMTP/IMAP credentials for sending outreach emails and detecting replies.
        </p>
      </div>

      {unreachable && <ErrorBanner message={message ?? undefined} />}
      {!unreachable && !loading && !data && <ErrorBanner message={message ?? 'Could not load configuration.'} />}

      {data && (
        <form onSubmit={handleSubmit} className="max-w-xl space-y-8">
          <div>
            <h2 className="mb-3 text-xs font-semibold tracking-widest text-indigo-400/90 uppercase">
              SMTP (sending)
            </h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="Host"
                  value={values.smtp_host ?? ''}
                  onChange={(v) => set('smtp_host', v)}
                  placeholder="smtp.gmail.com"
                />
                <Field
                  label="Port"
                  type="number"
                  value={values.smtp_port != null ? String(values.smtp_port) : ''}
                  onChange={(v) => set('smtp_port', v ? Number(v) : undefined)}
                  placeholder="587"
                />
              </div>
              <Field
                label="Email address"
                type="email"
                value={values.smtp_user ?? ''}
                onChange={(v) => set('smtp_user', v)}
                placeholder="you@gmail.com"
              />
              <div>
                <Label className="mb-1.5 text-xs font-medium text-slate-400">
                  App password
                  {data.smtp_app_password_set && (
                    <span className="ml-1.5 font-normal text-slate-600">(currently set — leave blank to keep)</span>
                  )}
                </Label>
                <Input
                  type="password"
                  value={appPassword}
                  onChange={(e) => {
                    setAppPassword(e.target.value);
                    setSaved(false);
                  }}
                  placeholder={data.smtp_app_password_set ? '••••••••••••••••' : 'Gmail app password'}
                  className="bg-white/[0.03]"
                  autoComplete="off"
                />
                <p className="mt-1.5 text-[11px] text-slate-600">
                  Generate one at{' '}
                  <a
                    href="https://myaccount.google.com/apppasswords"
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:underline"
                  >
                    myaccount.google.com/apppasswords
                  </a>
                </p>
              </div>
              <Field
                label="From name (optional)"
                value={values.smtp_from_name ?? ''}
                onChange={(v) => set('smtp_from_name', v)}
                placeholder="Your Name"
              />
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-xs font-semibold tracking-widest text-indigo-400/90 uppercase">
              IMAP (reply detection)
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <Field
                label="Host"
                value={values.imap_host ?? ''}
                onChange={(v) => set('imap_host', v)}
                placeholder="imap.gmail.com"
              />
              <Field
                label="Port"
                type="number"
                value={values.imap_port != null ? String(values.imap_port) : ''}
                onChange={(v) => set('imap_port', v ? Number(v) : undefined)}
                placeholder="993"
              />
            </div>
            <p className="mt-1.5 text-[11px] text-slate-600">Reuses the SMTP email/app password above.</p>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}
          {saved && !error && <p className="text-xs text-emerald-400">Saved.</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : 'Save configuration'}
          </Button>
        </form>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      <Label className="mb-1.5 text-xs font-medium text-slate-400">{label}</Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="bg-white/[0.03]"
      />
    </div>
  );
}
