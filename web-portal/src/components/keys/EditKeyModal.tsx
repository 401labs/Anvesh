'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { patchJson } from '@/lib/client';
import type { ApiKey, ApiKeyTier } from '@/lib/types';

interface EditKeyModalProps {
  apiKey: ApiKey | null;
  onClose: () => void;
  onSaved: () => void;
}

export function EditKeyModal({ apiKey, onClose, onSaved }: EditKeyModalProps) {
  const [name, setName] = useState('');
  const [tier, setTier] = useState<ApiKeyTier>('free');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (apiKey) {
      setName(apiKey.name);
      setTier(apiKey.tier);
      setError(null);
    }
  }, [apiKey]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!apiKey) return;
    setError(null);

    if (!name.trim()) {
      setError('Name is required.');
      return;
    }

    setSubmitting(true);
    const envelope = await patchJson(`/api/keys/${apiKey.id}`, { name: name.trim(), tier });
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    onSaved();
    onClose();
  }

  return (
    <Dialog open={apiKey != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit API key</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="bg-white/[0.03]" />
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

          {error && <p className="text-xs text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : 'Save changes'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
