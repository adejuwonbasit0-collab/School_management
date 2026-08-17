'use client';

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Users, GraduationCap, DollarSign, ClipboardList,
  TrendingUp, TrendingDown, AlertCircle, CheckCircle2,
  Calendar, Bell, BookOpen, BarChart3,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import { formatDistanceToNow, format } from 'date-fns';
import Link from 'next/link';
import { cn } from '@/lib/utils';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } };

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

export default function DashboardPage() {
  const { user } = useAuth();

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get<any>('/v1/schools/dashboard'),
  });

  const { data: financeStats } = useQuery({
    queryKey: ['finance-dashboard'],
    queryFn: () => api.get<any>('/v1/finance/dashboard'),
  });

  const { data: announcements } = useQuery({
    queryKey: ['announcements'],
    queryFn: () => api.get<any>('/v1/notifications/announcements'),
  });

  const statCards = [
    {
      title: 'Total Students',
      value: stats?.totalStudents?.toLocaleString() || '—',
      change: '+12 this month',
      trend: 'up',
      icon: Users,
      color: 'text-blue-600',
      bg: 'bg-blue-50 dark:bg-blue-950/30',
      href: '/dashboard/students',
    },
    {
      title: 'Total Staff',
      value: stats?.totalStaff?.toLocaleString() || '—',
      change: '+2 this month',
      trend: 'up',
      icon: GraduationCap,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
      href: '/dashboard/teachers',
    },
    {
      title: 'Revenue Collected',
      value: financeStats
        ? `${user?.school?.currencySymbol || '₦'}${Number(financeStats.totalCollected).toLocaleString()}`
        : '—',
      change: `${financeStats?.collectionRate || 0}% collection rate`,
      trend: financeStats?.collectionRate >= 80 ? 'up' : 'down',
      icon: DollarSign,
      color: 'text-amber-600',
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      href: '/dashboard/finance',
    },
    {
      title: 'Pending Fees',
      value: financeStats?.unpaidCount?.toLocaleString() || '—',
      change: `${financeStats?.overdueCount || 0} overdue`,
      trend: financeStats?.overdueCount > 0 ? 'down' : 'neutral',
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50 dark:bg-red-950/30',
      href: '/dashboard/finance/invoices',
    },
  ];

  const attendanceTrend = stats?.attendanceTrend || Array.from({ length: 7 }, (_, i) => ({
    date: format(new Date(Date.now() - (6 - i) * 86400000), 'EEE'),
    present: Math.floor(Math.random() * 50) + 200,
    absent: Math.floor(Math.random() * 30) + 10,
  }));

  const feeTrend = stats?.feeTrend || Array.from({ length: 6 }, (_, i) => ({
    month: format(new Date(2024, i, 1), 'MMM'),
    collected: Math.floor(Math.random() * 500000) + 200000,
    invoiced: Math.floor(Math.random() * 200000) + 600000,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          Good {new Date().getHours() < 12 ? 'Morning' : new Date().getHours() < 17 ? 'Afternoon' : 'Evening'},
          {' '}{user?.firstName} 👋
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          {format(new Date(), 'EEEE, MMMM d, yyyy')} • {user?.school?.name}
        </p>
      </div>

      {/* Stat Cards */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
      >
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <motion.div key={card.title} variants={item}>
              <Link href={card.href}>
                <div className="stat-card group cursor-pointer hover:border-primary/50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className={cn('p-2.5 rounded-lg', card.bg)}>
                      <Icon className={cn('w-5 h-5', card.color)} />
                    </div>
                    {card.trend === 'up' ? (
                      <TrendingUp className="w-4 h-4 text-emerald-500" />
                    ) : card.trend === 'down' ? (
                      <TrendingDown className="w-4 h-4 text-red-500" />
                    ) : null}
                  </div>
                  <p className="text-2xl font-bold text-foreground">{card.value}</p>
                  <p className="text-sm text-muted-foreground mt-1">{card.title}</p>
                  <p className={cn(
                    'text-xs mt-1.5 font-medium',
                    card.trend === 'up' ? 'text-emerald-600' : card.trend === 'down' ? 'text-red-500' : 'text-muted-foreground',
                  )}>
                    {card.change}
                  </p>
                </div>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Attendance Trend */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Attendance Trend</CardTitle>
            <CardDescription>Last 7 school days</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={attendanceTrend}>
                <defs>
                  <linearGradient id="present" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="absent" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Area type="monotone" dataKey="present" stroke="#3b82f6" fill="url(#present)" strokeWidth={2} name="Present" />
                <Area type="monotone" dataKey="absent" stroke="#ef4444" fill="url(#absent)" strokeWidth={2} name="Absent" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Quick Stats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: 'Active Classes', value: stats?.totalClasses || 0, icon: BookOpen, color: 'text-blue-600' },
              { label: 'Subjects', value: stats?.totalSubjects || 0, icon: BarChart3, color: 'text-purple-600' },
              { label: "Today's Attendance", value: `${stats?.todayAttendanceRate || 0}%`, icon: ClipboardList, color: 'text-emerald-600' },
              { label: 'Pending Admissions', value: stats?.pendingAdmissions || 0, icon: Calendar, color: 'text-amber-600' },
              { label: 'Unpaid Fees', value: stats?.unpaidFees || 0, icon: AlertCircle, color: 'text-red-600' },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex items-center gap-2">
                    <Icon className={cn('w-4 h-4', s.color)} />
                    <span className="text-sm text-muted-foreground">{s.label}</span>
                  </div>
                  <span className="text-sm font-semibold">{s.value}</span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Fee Collection Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Fee Collection</CardTitle>
            <CardDescription>Monthly invoiced vs collected</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={feeTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `₦${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                  formatter={(v: any) => [`₦${Number(v).toLocaleString()}`, '']}
                />
                <Bar dataKey="invoiced" fill="#e2e8f0" radius={[4, 4, 0, 0]} name="Invoiced" />
                <Bar dataKey="collected" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Collected" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Announcements */}
        <Card>
          <CardHeader className="pb-2 flex-row items-center justify-between">
            <CardTitle className="text-base font-semibold">Announcements</CardTitle>
            <Link href="/dashboard/announcements">
              <Button variant="ghost" size="sm" className="text-xs">View all</Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {announcements?.data?.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">No announcements</p>
            )}
            {(announcements?.data || []).slice(0, 5).map((a: any) => (
              <div key={a.id} className="border-l-2 border-primary pl-3 py-1">
                <p className="text-sm font-medium line-clamp-1">{a.title}</p>
                <p className="text-xs text-muted-foreground line-clamp-2">{a.content}</p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  {formatDistanceToNow(new Date(a.createdAt), { addSuffix: true })}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Recent Payments</CardTitle>
        </CardHeader>
        <CardContent>
          {financeStats?.recentPayments?.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">No recent payments</p>
          )}
          <div className="space-y-3">
            {(financeStats?.recentPayments || []).slice(0, 8).map((p: any) => (
              <div key={p.id} className="flex items-center gap-3 py-1">
                <Avatar className="w-8 h-8">
                  <AvatarFallback className="text-xs bg-primary/10 text-primary">
                    {p.invoice?.student?.user?.firstName?.[0]}{p.invoice?.student?.user?.lastName?.[0]}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {p.invoice?.student?.user?.firstName} {p.invoice?.student?.user?.lastName}
                  </p>
                  <p className="text-xs text-muted-foreground">{p.invoice?.invoiceNo}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-emerald-600">
                    +{user?.school?.currencySymbol || '₦'}{Number(p.amount).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {p.paidAt ? formatDistanceToNow(new Date(p.paidAt), { addSuffix: true }) : ''}
                  </p>
                </div>
                <Badge variant="secondary" className="badge-success text-xs">Paid</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
