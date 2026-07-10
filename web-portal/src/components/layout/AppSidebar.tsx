'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Radar, LayoutGrid, ListTodo, CalendarClock, Users, Mail, KeyRound, Settings } from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

const LINKS = [
  { href: '/', label: 'Overview', icon: LayoutGrid },
  { href: '/tasks', label: 'Tasks', icon: ListTodo },
  { href: '/schedules', label: 'Schedules', icon: CalendarClock },
  { href: '/leads', label: 'Leads', icon: Users },
  { href: '/outreach', label: 'Outreach', icon: Mail },
  { href: '/keys', label: 'Keys', icon: KeyRound },
];

const FOOTER_LINKS = [{ href: '/settings', label: 'Settings', icon: Settings }];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon" className="border-white/10">
      <SidebarHeader>
        <Link href="/" className="flex items-center gap-2 p-2">
          <Radar className="h-4 w-4 shrink-0 text-indigo-400" />
          <span className="text-sm font-semibold tracking-tight text-white group-data-[collapsible=icon]:hidden">
            Anvesh Portal
          </span>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {LINKS.map(({ href, label, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton isActive={pathname === href} render={<Link href={href} />}>
                    <Icon />
                    <span>{label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {FOOTER_LINKS.map(({ href, label, icon: Icon }) => (
            <SidebarMenuItem key={href}>
              <SidebarMenuButton isActive={pathname === href} render={<Link href={href} />}>
                <Icon />
                <span>{label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
