'use client';

import { useState, type FormEvent } from 'react';
import { Plus, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { postJson } from '@/lib/client';
import type { ApiKeyCreated, ApiKeyTier } from '@/lib/types';

interface NewKeyFormProps {
  onCreated: () => void;
}

export function NewKeyForm({ onCreated }: NewKeyFormProps) {
  const [name, setName] = useState('');
  const [tier, setTier] = useState<ApiKeyTier>('free');
  const [expiresInDays, setExpiresInDays] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Name is required.');
      return;
    }

    setSubmitting(true);
    const envelope = await postJson<ApiKeyCreated>('/api/keys', {
      name: name.trim(),
      tier,
      ...(expiresInDays ? { expires_in_days: Number(expiresInDays) } : {}),
    });
    setSubmitting(false);

    if (!envelope.success || !envelope.data) {
      setError(envelope.message);
      return;
    }

    setCreated(envelope.data);
    setName('');
    setExpiresInDays('');
    onCreated();
  }

  function copyKey() {
    if (!created) return;
    navigator.clipboard.writeText(created.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="border-b border-white/10 pb-6">
      <h2 className="mb-4 text-sm font-semibold text-white">Create an API key</h2>

      {created ? (
        <div className="space-y-3">
          <p className="text-xs text-amber-300">
            This key is only shown once. Copy it now — you won&apos;t be able to see it again.
          </p>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3.5 py-2.5">
            <code className="flex-1 truncate text-sm text-slate-200">{created.key}</code>
            <button
              onClick={copyKey}
              className="rounded-full p-1.5 text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
              aria-label="Copy key"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          </div>
          <Button variant="secondary" onClick={() => setCreated(null)}>
            Done
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Name</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Web Portal"
                className="bg-white/[0.03]"
              />
            </div>
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Tier</Label>
              <Select value={tier} onValueChange={(v) => setTier(v as ApiKeyTier)}>
                <SelectTrigger className="w-full bg-white/[0.03]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="pro">Pro</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 text-xs font-medium text-slate-400">Expires in (days)</Label>
              <Input
                type="number"
                min={1}
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(e.target.value)}
                placeholder="Never"
                className="bg-white/[0.03]"
              />
            </div>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            <Plus className="h-3.5 w-3.5" />
            {submitting ? 'Creating…' : 'Create key'}
          </Button>
        </form>
      )}
    </div>
  );
}
