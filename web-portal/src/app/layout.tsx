import './global.css';
import { Inter } from 'next/font/google';
import type { Metadata } from 'next';
import { Nav } from '@/components/layout/Nav';
import { cn } from '@/lib/utils';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  fallback: ['system-ui', 'arial'],
  variable: '--font-sans',
});

export const metadata: Metadata = {
  title: {
    default: 'Anvesh Portal',
    template: '%s | Anvesh Portal',
  },
  description: 'Operate the Anvesh lead-scraping automation server: tasks, leads, and API keys.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn('dark', inter.variable, 'font-sans')} suppressHydrationWarning>
      <body className="flex min-h-screen flex-col bg-dark-bg text-slate-200 antialiased" suppressHydrationWarning>
        <div className="grid-bg pointer-events-none fixed inset-0 opacity-30" />
        <Nav />
        <main className="relative z-10 flex-1">{children}</main>
      </body>
    </html>
  );
}
