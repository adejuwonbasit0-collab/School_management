'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, Users, GraduationCap, BookOpen, ClipboardList,
  BarChart3, DollarSign, UserCog, Building2, Bus, Hotel,
  Library, Package, Settings, Bell, Bot, FileText, Calendar,
  LogOut, ChevronRight, School, X, Trophy, Megaphone, Cog,
  ShieldCheck, Zap, Clock, FolderOpen, MessageSquare, Award,
  BarChart2, Stethoscope, Shield, Link as LinkIcon, Palette, Database, Wallet,
  GraduationCap as GradCap, BookMarked, Home as HomeIcon, User,
} from 'lucide-react';
import { useAuth, useAuthStore } from '@/store/auth.store';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import api from '@/lib/api-client';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  permission?: string;
  children?: NavItem[];
}

const NAV_GROUPS: Array<{ label: string; items: NavItem[] }> = [
  {
    label: 'Overview',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Calendar', href: '/dashboard/calendar', icon: Calendar },
      { label: 'Announcements', href: '/dashboard/announcements', icon: Megaphone },
    ],
  },
  {
    label: 'Academic',
    items: [
      { label: 'Students', href: '/dashboard/students', icon: Users, permission: 'students:students:READ' },
      { label: 'Teachers', href: '/dashboard/teachers', icon: GraduationCap, permission: 'teachers:teachers:READ' },
      { label: 'Classes', href: '/dashboard/classes', icon: Building2, permission: 'classes:classes:READ' },
      { label: 'Subjects', href: '/dashboard/subjects', icon: BookOpen, permission: 'subjects:subjects:READ' },
      { label: 'Attendance', href: '/dashboard/attendance', icon: ClipboardList, permission: 'attendance:attendance:READ' },
      { label: 'Examinations', href: '/dashboard/examinations', icon: Trophy, permission: 'examinations:examinations:READ' },
      { label: 'Results', href: '/dashboard/results', icon: Award, permission: 'results:results:READ' },
      { label: 'LMS / Courses', href: '/dashboard/lms', icon: BookMarked, permission: 'lms:courses:READ' },
      { label: 'Timetable', href: '/dashboard/timetable', icon: Clock, permission: 'timetable:timetable:READ' },
      { label: 'Grades', href: '/dashboard/grades', icon: BarChart3, permission: 'grades:grades:READ' },
      { label: 'Assignments', href: '/dashboard/assignments', icon: FileText },
    ],
  },
  {
    label: 'Admissions',
    items: [
      { label: 'Applications', href: '/dashboard/admissions', icon: School, permission: 'admissions:admissions:READ' },
    ],
  },
  {
    label: 'Finance',
    items: [
      { label: 'Overview', href: '/dashboard/finance', icon: DollarSign, permission: 'finance:reports:READ' },
      { label: 'Invoices', href: '/dashboard/finance/invoices', icon: FileText, permission: 'finance:invoices:READ' },
      { label: 'Expenses', href: '/dashboard/finance/expenses', icon: Package, permission: 'finance:expenses:READ' },
      { label: 'Fee Structures', href: '/dashboard/finance/fee-structures', icon: Cog, permission: 'finance:fee-structures:READ' },
      { label: 'Gateways', href: '/dashboard/finance/gateways', icon: ShieldCheck, permission: 'finance:gateways:READ' },
    ],
  },
  {
    label: 'Human Resources',
    items: [
      { label: 'Staff', href: '/dashboard/hr/staff', icon: UserCog, permission: 'hr:staff:READ' },
      { label: 'Leave', href: '/dashboard/hr/leave', icon: Calendar, permission: 'hr:leave:READ' },
      { label: 'Payroll', href: '/dashboard/hr/payroll', icon: DollarSign, permission: 'hr:payroll:READ' },
    ],
  },
  {
    label: 'Campus',
    items: [
      { label: 'Library', href: '/dashboard/library', icon: Library, permission: 'library:library:READ' },
      { label: 'Transport', href: '/dashboard/transport', icon: Bus, permission: 'transport:transport:READ' },
      { label: 'Hostel', href: '/dashboard/hostel', icon: Hotel, permission: 'hostel:hostel:READ' },
      { label: 'Inventory', href: '/dashboard/inventory', icon: Package, permission: 'inventory:inventory:READ' },
    ],
  },
  {
    label: 'Communication',
    items: [
      { label: 'Communications', href: '/dashboard/communications', icon: MessageSquare, permission: 'communications:broadcasts:READ' },
      { label: 'Documents', href: '/dashboard/documents', icon: FolderOpen, permission: 'documents:documents:READ' },
      { label: 'Notifications', href: '/dashboard/notifications', icon: Bell },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'Reports', href: '/dashboard/reports', icon: BarChart3, permission: 'reports:reports:READ' },
      { label: 'AI Center', href: '/dashboard/ai', icon: Bot, permission: 'ai:ai:READ' },
      { label: 'Automation', href: '/dashboard/automation', icon: Zap, permission: 'automation:automation:READ' },
    ],
  },
  {
    label: 'Portals',
    items: [
      { label: 'Teacher Portal', href: '/dashboard/teacher', icon: User },
      { label: 'Student Portal', href: '/dashboard/student', icon: User },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Clinic', href: '/dashboard/clinic', icon: Stethoscope, permission: 'clinic:clinic:READ' },
      { label: 'Analytics', href: '/dashboard/analytics', icon: BarChart2, permission: 'analytics:analytics:READ' },
      { label: 'HR Payslips', href: '/dashboard/hr/payslips', icon: Wallet, permission: 'hr:payroll:READ' },
      { label: 'Scholarships', href: '/dashboard/finance/scholarships', icon: GradCap, permission: 'finance:invoices:READ' },
      { label: 'Debtors', href: '/dashboard/finance/debtors', icon: Wallet, permission: 'analytics:analytics:READ' },
    ],
  },
  {
    label: 'System',
    items: [
      { label: 'Audit Logs', href: '/dashboard/audit', icon: Shield, permission: 'audit:audit:READ' },
      { label: 'Integrations', href: '/dashboard/integrations', icon: LinkIcon, permission: 'integrations:integrations:READ' },
      { label: 'Customization', href: '/dashboard/customization', icon: Palette, permission: 'customization:customization:READ' },
      { label: 'Backup', href: '/dashboard/backup', icon: Database, permission: 'backup:backup:READ' },
    ],
  },
  {
    label: 'Administration',
    items: [
      { label: 'Settings', href: '/dashboard/settings', icon: Settings, permission: 'settings:settings:READ' },
      { label: 'Roles & Permissions', href: '/dashboard/settings/roles', icon: ShieldCheck, permission: 'settings:roles:MANAGE' },
      { label: 'Departments', href: '/dashboard/settings?tab=departments', icon: Settings, permission: 'settings:settings:READ' },
      { label: 'Academic Years', href: '/dashboard/settings?tab=academic-years', icon: Settings, permission: 'settings:settings:READ' },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onClose?: () => void;
}

export function Sidebar({ collapsed, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const router = useRouter();
  const { hasPermission } = useAuth();

  const handleLogout = async () => {
    try {
      await api.post('/v1/auth/logout');
    } finally {
      clearAuth();
      router.push('/auth/login');
    }
  };

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  const canSee = (item: NavItem) => {
    if (!item.permission) return true;
    return hasPermission(item.permission);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-sidebar-border">
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2"
          >
            <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-sidebar-foreground">EduCore</span>
          </motion.div>
        )}
        {collapsed && (
          <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center mx-auto">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
        )}
        {onClose && (
          <button onClick={onClose} className="text-sidebar-foreground/50 hover:text-sidebar-foreground">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* School Name */}
      {!collapsed && user?.school && (
        <div className="px-4 py-2 border-b border-sidebar-border">
          <p className="text-xs text-sidebar-foreground/50 uppercase tracking-wider">School</p>
          <p className="text-sm font-medium text-sidebar-foreground truncate">{user.school.name}</p>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(canSee);
          if (visibleItems.length === 0) return null;

          return (
            <div key={group.label} className="mb-4">
              {!collapsed && (
                <p className="px-3 mb-1 text-xs font-semibold text-sidebar-foreground/40 uppercase tracking-wider">
                  {group.label}
                </p>
              )}
              {visibleItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link key={item.href} href={item.href}>
                    <div
                      className={cn(
                        'sidebar-item',
                        active && 'active',
                        collapsed && 'justify-center px-2',
                      )}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon className={cn('w-4 h-4 flex-shrink-0', active && 'text-sidebar-primary')} />
                      {!collapsed && (
                        <>
                          <span className="flex-1">{item.label}</span>
                          {item.badge && (
                            <Badge variant="secondary" className="text-xs py-0 px-1.5">
                              {item.badge}
                            </Badge>
                          )}
                        </>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="border-t border-sidebar-border p-3">
        <div
          className={cn(
            'flex items-center gap-3 rounded-lg p-2 cursor-pointer hover:bg-sidebar-accent',
            collapsed && 'justify-center',
          )}
        >
          <Avatar className="w-8 h-8 flex-shrink-0">
            <AvatarImage src={user?.avatar} />
            <AvatarFallback className="text-xs bg-sidebar-primary text-white">
              {user?.firstName?.[0]}{user?.lastName?.[0]}
            </AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-sidebar-foreground truncate">
                {user?.firstName} {user?.lastName}
              </p>
              <p className="text-xs text-sidebar-foreground/50 truncate">{user?.email}</p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={handleLogout}
              className="text-sidebar-foreground/50 hover:text-red-400 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
