'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DollarSign, TrendingUp, TrendingDown, AlertCircle, CheckCircle2,
  Plus, Search, Filter, Download, Eye, MoreHorizontal, Receipt,
  CreditCard, RefreshCw, FileText, BarChart3, ArrowUpRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import { RecordPaymentDialog } from '@/components/finance/record-payment-dialog';
import { CreateInvoiceDialog } from '@/components/finance/create-invoice-dialog';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const statusClass: Record<string, string> = {
  PAID: 'badge-success',
  PARTIAL: 'badge-warning',
  UNPAID: 'badge-danger',
  OVERDUE: 'badge-danger',
  WAIVED: 'badge-neutral',
};

export default function FinancePage() {
  const [invoiceSearch, setInvoiceSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedInvoice, setSelectedInvoice] = useState<any>(null);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [createInvoiceOpen, setCreateInvoiceOpen] = useState(false);
  const { user, hasPermission } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['finance-dashboard'],
    queryFn: () => api.get<any>('/v1/finance/dashboard'),
  });

  const { data: invoicesData, isLoading: invLoading } = useQuery({
    queryKey: ['invoices', { search: invoiceSearch, status: statusFilter, page }],
    queryFn: () => api.get<any>('/v1/finance/invoices', {
      search: invoiceSearch,
      status: statusFilter || undefined,
      page,
      limit: 15,
    }),
    placeholderData: (prev) => prev,
  });

  const invoices = invoicesData?.data || [];
  const meta = invoicesData?.meta;

  const statCards = [
    {
      label: 'Total Invoiced',
      value: statsLoading ? '—' : `${sym}${Number(stats?.totalInvoiced || 0).toLocaleString()}`,
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-50 dark:bg-blue-950/30',
      sub: 'All time',
    },
    {
      label: 'Total Collected',
      value: statsLoading ? '—' : `${sym}${Number(stats?.totalCollected || 0).toLocaleString()}`,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
      sub: `${stats?.collectionRate || 0}% collection rate`,
      trend: (stats?.collectionRate || 0) >= 80 ? 'up' : 'down',
    },
    {
      label: 'Outstanding',
      value: statsLoading ? '—' : `${sym}${Number(stats?.outstanding || 0).toLocaleString()}`,
      icon: AlertCircle,
      color: 'text-amber-600',
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      sub: `${stats?.unpaidCount || 0} unpaid invoices`,
    },
    {
      label: 'Overdue',
      value: statsLoading ? '—' : `${stats?.overdueCount || 0}`,
      icon: TrendingDown,
      color: 'text-red-600',
      bg: 'bg-red-50 dark:bg-red-950/30',
      sub: 'Past due date',
      trend: (stats?.overdueCount || 0) > 0 ? 'down' : 'neutral',
    },
  ];

  // Pie data for payment gateways
  const gatewayData = Object.entries(stats?.byGateway || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Finance</h1>
          <p className="section-subtitle">Track fees, payments and expenses</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" /> Export
          </Button>
          {hasPermission('finance:invoices:CREATE') && (
            <Button size="sm" onClick={() => setCreateInvoiceOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> New Invoice
            </Button>
          )}
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {statCards.map((s) => {
          const Icon = s.icon;
          return (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="stat-card"
            >
              <div className="flex items-start justify-between mb-3">
                <div className={cn('p-2.5 rounded-lg', s.bg)}>
                  <Icon className={cn('w-5 h-5', s.color)} />
                </div>
                {s.trend === 'up' ? (
                  <TrendingUp className="w-4 h-4 text-emerald-500" />
                ) : s.trend === 'down' ? (
                  <TrendingDown className="w-4 h-4 text-red-500" />
                ) : null}
              </div>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-sm text-muted-foreground mt-1">{s.label}</p>
              {s.sub && <p className="text-xs text-muted-foreground/70 mt-0.5">{s.sub}</p>}
            </motion.div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Collection Trend */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Collection Trend</CardTitle>
            <CardDescription>Monthly fee collection overview</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={stats?.monthlyTrend || []}>
                <defs>
                  <linearGradient id="collected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="invoiced" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${sym}${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(v: any) => [`${sym}${Number(v).toLocaleString()}`, '']}
                />
                <Area type="monotone" dataKey="invoiced" stroke="#3b82f6" fill="url(#invoiced)" strokeWidth={2} name="Invoiced" />
                <Area type="monotone" dataKey="collected" stroke="#10b981" fill="url(#collected)" strokeWidth={2} name="Collected" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Payment Methods */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Payment Methods</CardTitle>
          </CardHeader>
          <CardContent>
            {gatewayData.length === 0 ? (
              <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
                No payment data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={gatewayData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value" nameKey="name">
                    {gatewayData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any) => `${sym}${Number(v).toLocaleString()}`} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Payments */}
      {stats?.recentPayments?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Recent Payments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {stats.recentPayments.slice(0, 5).map((p: any) => (
                <div key={p.id} className="flex items-center gap-3 py-2 border-b last:border-0">
                  <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center flex-shrink-0">
                    <CreditCard className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {p.invoice?.student?.user?.firstName} {p.invoice?.student?.user?.lastName}
                    </p>
                    <p className="text-xs text-muted-foreground">{p.invoice?.invoiceNo} • {p.gateway}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-emerald-600">+{sym}{Number(p.amount).toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.paidAt ? format(new Date(p.paidAt), 'dd MMM, HH:mm') : ''}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invoices Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="text-base font-semibold">Invoices</CardTitle>
              <CardDescription>{meta?.total || 0} total invoices</CardDescription>
            </div>
            <div className="flex gap-2 flex-wrap">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search invoices..."
                  className="pl-8 h-8 w-52 text-sm"
                  value={invoiceSearch}
                  onChange={(e) => { setInvoiceSearch(e.target.value); setPage(1); }}
                />
              </div>
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v === 'all' ? '' : v); setPage(1); }}>
                <SelectTrigger className="h-8 w-36 text-sm">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="UNPAID">Unpaid</SelectItem>
                  <SelectItem value="PARTIAL">Partial</SelectItem>
                  <SelectItem value="PAID">Paid</SelectItem>
                  <SelectItem value="OVERDUE">Overdue</SelectItem>
                  <SelectItem value="WAIVED">Waived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead>Invoice</TableHead>
                <TableHead>Student</TableHead>
                <TableHead>Class</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Paid</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 9 }).map((_, j) => (
                        <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                : invoices.length === 0
                ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                      <Receipt className="w-10 h-10 mx-auto mb-2 opacity-20" />
                      <p>No invoices found</p>
                    </TableCell>
                  </TableRow>
                )
                : invoices.map((inv: any) => {
                    const balance = Number(inv.totalAmount) - Number(inv.paidAmount);
                    const enrollment = inv.student?.enrollments?.[0];
                    return (
                      <TableRow key={inv.id} className="hover:bg-muted/30">
                        <TableCell>
                          <Link href={`/dashboard/finance/invoices/${inv.id}`} className="font-mono text-sm text-primary hover:underline">
                            {inv.invoiceNo}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm font-medium">
                            {inv.student?.user?.firstName} {inv.student?.user?.lastName}
                          </p>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {enrollment?.classRoom?.name} {enrollment?.classRoom?.section || ''}
                        </TableCell>
                        <TableCell className="text-right font-medium text-sm">
                          {sym}{Number(inv.totalAmount).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right text-emerald-600 text-sm">
                          {sym}{Number(inv.paidAmount).toLocaleString()}
                        </TableCell>
                        <TableCell className={cn('text-right text-sm font-medium', balance > 0 ? 'text-red-600' : 'text-emerald-600')}>
                          {sym}{balance.toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={cn('text-xs', statusClass[inv.status] || 'badge-neutral')}>
                            {inv.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {inv.dueDate ? format(new Date(inv.dueDate), 'dd MMM yyyy') : '—'}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="w-7 h-7">
                                <MoreHorizontal className="w-3.5 h-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem asChild>
                                <Link href={`/dashboard/finance/invoices/${inv.id}`}>
                                  <Eye className="w-4 h-4 mr-2" /> View
                                </Link>
                              </DropdownMenuItem>
                              {hasPermission('finance:payments:CREATE') && inv.status !== 'PAID' && inv.status !== 'WAIVED' && (
                                <DropdownMenuItem onClick={() => { setSelectedInvoice(inv); setPaymentOpen(true); }}>
                                  <CreditCard className="w-4 h-4 mr-2" /> Record Payment
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem>
                                <Download className="w-4 h-4 mr-2" /> Download Receipt
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
            </TableBody>
          </Table>

          {meta && meta.totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * 15 + 1}–{Math.min(page * 15, meta.total)} of {meta.total}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => p - 1)} disabled={page === 1}>Previous</Button>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page >= meta.totalPages}>Next</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <RecordPaymentDialog
        open={paymentOpen}
        invoice={selectedInvoice}
        onClose={() => { setPaymentOpen(false); setSelectedInvoice(null); }}
      />
      <CreateInvoiceDialog open={createInvoiceOpen} onClose={() => setCreateInvoiceOpen(false)} />
    </div>
  );
}
