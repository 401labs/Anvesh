'use client';

import { useRef, useState, type KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface LocationsInputProps {
  value: string[];
  onChange: (locations: string[]) => void;
  placeholder?: string;
}

export function LocationsInput({ value, onChange, placeholder }: LocationsInputProps) {
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  function commitDraft() {
    const trimmed = draft.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setDraft('');
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commitDraft();
    } else if (e.key === 'Backspace' && draft === '' && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  function removeAt(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <div
      className="flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-lg border border-input bg-white/[0.03] px-2.5 py-1.5 transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50"
      onClick={() => inputRef.current?.focus()}
    >
      {value.map((loc, i) => (
        <span
          key={`${loc}-${i}`}
          className="inline-flex items-center gap-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 py-0.5 pr-1 pl-2 text-xs text-indigo-300"
        >
          {loc}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              removeAt(i);
            }}
            className="rounded-full p-0.5 hover:bg-indigo-500/20"
            aria-label={`Remove ${loc}`}
          >
            <X className="h-2.5 w-2.5" />
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        placeholder={value.length === 0 ? placeholder : ''}
        className="min-w-[100px] flex-1 bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600"
      />
    </div>
  );
}
