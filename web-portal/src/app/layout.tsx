import './global.css';
import { Inter } from 'next/font/google';
import type { Metadata } from 'next';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';
import { TooltipProvider } from '@/components/ui/tooltip';
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
      <body className="bg-dark-bg text-slate-200 antialiased" suppressHydrationWarning>
        <div className="grid-bg pointer-events-none fixed inset-0 opacity-30" />
        <TooltipProvider>
          <SidebarProvider>
            <AppSidebar />
            <SidebarInset className="relative z-10 bg-transparent">
              <header className="sticky top-0 z-20 flex h-12 shrink-0 items-center gap-2 border-b border-white/10 bg-[#0b0b0e]/70 px-4 backdrop-blur-xl">
                <SidebarTrigger className="text-slate-400 hover:text-slate-200" />
                <Separator orientation="vertical" className="h-4 bg-white/10" />
                <span className="text-xs font-medium text-slate-500">Anvesh Portal</span>
              </header>
              <main className="flex-1">{children}</main>
            </SidebarInset>
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
