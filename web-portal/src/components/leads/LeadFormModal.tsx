'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { postJson, patchJson } from '@/lib/client';
import type { Lead, LeadCreate, LeadStatus } from '@/lib/types';

const STATUS_OPTIONS: LeadStatus[] = ['new', 'contacted', 'replied', 'interested', 'won', 'lost'];

const EMPTY: LeadCreate = {
  business_name: '',
  industry: '',
  location: '',
  address: '',
  category: '',
  rating: undefined,
  review_count: undefined,
  has_website: false,
  website_url: '',
  phone: '',
  email: '',
  maps_url: '',
  status: 'new',
};

interface LeadFormModalProps {
  /** When set, the modal is open in edit mode for this lead. */
  editingLead?: Lead | null;
  /** When true, the modal is open in create mode. */
  createOpen?: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function LeadFormModal({ editingLead, createOpen, onClose, onSaved }: LeadFormModalProps) {
  const [values, setValues] = useState<LeadCreate>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = createOpen || editingLead != null;
  const isEdit = editingLead != null;

  useEffect(() => {
    if (editingLead) {
      setValues({
        business_name: editingLead.business_name,
        industry: editingLead.industry,
        location: editingLead.location,
        address: editingLead.address,
        category: editingLead.category ?? '',
        rating: editingLead.rating ?? undefined,
        review_count: editingLead.review_count ?? undefined,
        is_claimed: editingLead.is_claimed ?? undefined,
        has_website: editingLead.has_website,
        website_url: editingLead.website_url ?? '',
        phone: editingLead.phone ?? '',
        email: editingLead.email ?? '',
        maps_url: editingLead.maps_url ?? '',
        status: editingLead.status,
      });
    } else if (createOpen) {
      setValues(EMPTY);
    }
    setError(null);
  }, [editingLead, createOpen]);

  function set<K extends keyof LeadCreate>(key: K, value: LeadCreate[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!values.business_name.trim() || !values.industry.trim() || !values.location.trim() || !values.address.trim()) {
      setError('Business name, industry, location, and address are required.');
      return;
    }

    setSubmitting(true);
    const envelope = isEdit
      ? await patchJson(`/api/leads/${editingLead!.id}`, values)
      : await postJson('/api/leads', values);
    setSubmitting(false);

    if (!envelope.success) {
      setError(envelope.message);
      return;
    }

    onSaved();
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit lead' : 'Add lead'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Business name" value={values.business_name} onChange={(v) => set('business_name', v)} />
            <Field label="Industry" value={values.industry} onChange={(v) => set('industry', v)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Location" value={values.location} onChange={(v) => set('location', v)} />
            <Field label="Category" value={values.category ?? ''} onChange={(v) => set('category', v)} />
          </div>
          <Field label="Address" value={values.address} onChange={(v) => set('address', v)} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Phone" value={values.phone ?? ''} onChange={(v) => set('phone', v)} />
            <Field label="Email" type="email" value={values.email ?? ''} onChange={(v) => set('email', v)} />
          </div>
          <Field label="Website URL" value={values.website_url ?? ''} onChange={(v) => set('website_url', v)} />
          <Field label="Maps URL" value={values.maps_url ?? ''} onChange={(v) => set('maps_url', v)} />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Rating"
              type="number"
              value={values.rating?.toString() ?? ''}
              onChange={(v) => set('rating', v ? Number(v) : undefined)}
            />
            <Field
              label="Review count"
              type="number"
              value={values.review_count?.toString() ?? ''}
              onChange={(v) => set('review_count', v ? Number(v) : undefined)}
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <Checkbox
              checked={values.has_website ?? false}
              onCheckedChange={(c) => set('has_website', c === true)}
            />
            Has a website
          </label>

          <div>
            <Label className="mb-1.5 text-xs font-medium text-slate-400">Status</Label>
            <Select value={values.status ?? 'new'} onValueChange={(v) => set('status', v as LeadStatus)}>
              <SelectTrigger className="w-full bg-white/[0.03]">
                <SelectValue>
                  {(values.status ?? 'new').charAt(0).toUpperCase() + (values.status ?? 'new').slice(1)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create lead'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <div>
      <Label className="mb-1.5 text-xs font-medium text-slate-400">{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="bg-white/[0.03]" />
    </div>
  );
}
