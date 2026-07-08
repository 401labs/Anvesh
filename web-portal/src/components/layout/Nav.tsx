'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Radar, LayoutGrid, ListTodo, Users, KeyRound } from 'lucide-react';
import { cn } from '@/lib/utils';

const LINKS = [
  { href: '/', label: 'Overview', icon: LayoutGrid },
  { href: '/tasks', label: 'Tasks', icon: ListTodo },
  { href: '/leads', label: 'Leads', icon: Users },
  { href: '/keys', label: 'Keys', icon: KeyRound },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40">
      <div className="flex w-full items-center justify-between px-6 py-4 md:px-10">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600/10">
            <Radar className="h-4 w-4 text-indigo-400" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-white">Anvesh Portal</span>
        </Link>

        <nav className="flex items-center gap-1">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors',
                  active ? 'bg-white/[0.06] text-white' : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
