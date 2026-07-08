import { cn } from '@/lib/utils';

interface StatCardProps {
  value: string;
  label: string;
  description?: string;
  highlight?: boolean;
}

export function StatCard({ value, label, description, highlight = false }: StatCardProps) {
  return (
    <div className={cn('stat-card', highlight && 'ring-1 ring-indigo-500/20 bg-[#16161A]')}>
      {highlight && <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-indigo-500/5 to-transparent" />}
      <h3 className="mb-2 text-4xl font-semibold tracking-tight text-white md:text-5xl">{value}</h3>
      <p className={cn('text-sm font-medium uppercase tracking-wider', highlight ? 'text-indigo-300' : 'text-slate-500')}>
        {label}
      </p>
      {description && <p className="mt-2 max-w-[180px] text-center text-xs text-slate-600">{description}</p>}
    </div>
  );
}
