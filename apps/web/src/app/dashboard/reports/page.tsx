'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Download, FileText, Users, DollarSign, ClipboardList } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import { exportToCSV, formatCurrency } from '@/lib/utils';
import toast from 'react-hot-toast';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function ReportsPage() {
  const { user } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const today = new Date().toISOString().split('T')[0];
  const firstOfYear = `${new Date().getFullYear()}-01-01`;

  const [feeStart, setFeeStart] = useState(firstOfYear);
  const [feeEnd, setFeeEnd] = useState(today);
  const [attTermId, setAttTermId] = useState('');

  const { data: analytics } = useQuery({
    queryKey: ['reports-analytics'],
    queryFn: () => api.get<any>('/v1/reports/analytics'),
  });

  const { data: feeReport, refetch: refetchFees, isFetching: feeLoading } = useQuery({
    queryKey: ['fee-report', feeStart, feeEnd],
    queryFn: () => api.get<any>(`/v1/reports/fees?startDate=${feeStart}&endDate=${feeEnd}`),
    enabled: false,
  });

  const { data: terms } = useQuery({
    queryKey: ['terms'],
    queryFn: () => api.get<any>('/v1/schools/terms'),
  });

  const { data: attReport, refetch: refetchAtt, isFetching: attLoading } = useQuery({
    queryKey: ['att-report', attTermId],
    queryFn: () => api.get<any>(`/v1/reports/attendance?termId=${attTermId}`),
    enabled: false,
  });

  const handleExportFees = () => {
    if (!feeReport?.payments) { toast.error('Generate the report first'); return; }
    exportToCSV(feeReport.payments, `fee-report-${feeStart}-${feeEnd}`);
    toast.success('CSV downloaded');
  };

  const handleExportAttendance = () => {
    if (!attReport?.summary) { toast.error('Generate the report first'); return; }
    exportToCSV(attReport.summary, `attendance-report`);
    toast.success('CSV downloaded');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Reports & Analytics</h1>
          <p className="section-subtitle">Generate and export school reports</p>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview"><BarChart3 className="w-4 h-4 mr-1.5" />Overview</TabsTrigger>
          <TabsTrigger value="fees"><DollarSign className="w-4 h-4 mr-1.5" />Fee Report</TabsTrigger>
          <TabsTrigger value="attendance"><ClipboardList className="w-4 h-4 mr-1.5" />Attendance Report</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="space-y-6 mt-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Total Students Enrolled', value: analytics?.enrollmentByClass?.reduce((s: number, c: any) => s + c._count, 0) || 0, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
              { label: 'Total Collected (YTD)', value: `${sym}${Number(analytics?.yearlyCollection || 0).toLocaleString()}`, icon: DollarSign, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
              { label: 'Active Staff', value: analytics?.staffByDepartment?.reduce((s: number, d: any) => s + d._count, 0) || 0, icon: Users, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-950/30' },
              { label: 'Attendance (30d)', value: `${analytics?.attendanceRate || 0}%`, icon: ClipboardList, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <Card key={s.label} className="shadow-card">
                  <CardContent className="pt-4 pb-4">
                    <div className={`inline-flex p-2 rounded-lg ${s.bg} mb-2`}>
                      <Icon className={`w-4 h-4 ${s.color}`} />
                    </div>
                    <p className="text-xl font-bold">{s.value}</p>
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Enrollment by class */}
          {analytics?.enrollmentByClass?.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Enrollment by Class</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={analytics.enrollmentByClass.slice(0, 12)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="classRoomId" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }} />
                    <Bar dataKey="_count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Students" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Staff by department */}
          {analytics?.staffByDepartment?.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Staff Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={analytics.staffByDepartment} cx="50%" cy="50%" outerRadius={80} dataKey="_count" nameKey="departmentId">
                      {analytics.staffByDepartment.map((_: any, i: number) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Fee Report */}
        <TabsContent value="fees" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Fee Collection Report</CardTitle>
              <CardDescription>Generate a detailed report of all fee payments</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4 flex-wrap items-end">
                <div className="space-y-1.5">
                  <Label>From Date</Label>
                  <Input type="date" value={feeStart} onChange={(e) => setFeeStart(e.target.value)} className="w-44" />
                </div>
                <div className="space-y-1.5">
                  <Label>To Date</Label>
                  <Input type="date" value={feeEnd} onChange={(e) => setFeeEnd(e.target.value)} className="w-44" />
                </div>
                <Button onClick={() => refetchFees()} disabled={feeLoading}>
                  {feeLoading ? 'Generating...' : 'Generate Report'}
                </Button>
                {feeReport && (
                  <Button variant="outline" onClick={handleExportFees}>
                    <Download className="w-4 h-4 mr-2" />Export CSV
                  </Button>
                )}
              </div>

              {feeReport && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
                    <div><p className="text-sm font-semibold">{sym}{Number(feeReport.totalCollected || 0).toLocaleString()}</p><p className="text-xs text-muted-foreground">Total Collected</p></div>
                    <div><p className="text-sm font-semibold">{feeReport.totalTransactions || 0}</p><p className="text-xs text-muted-foreground">Transactions</p></div>
                    <div><p className="text-sm font-semibold">{feeReport.period?.start} – {feeReport.period?.end}</p><p className="text-xs text-muted-foreground">Period</p></div>
                  </div>

                  <div className="rounded-lg border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/30">
                        <tr>
                          {['Date', 'Student', 'Class', 'Invoice', 'Amount', 'Method', 'Reference'].map((h) => (
                            <th key={h} className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {(feeReport.payments || []).slice(0, 50).map((p: any, i: number) => (
                          <tr key={i} className="hover:bg-muted/20">
                            <td className="px-3 py-2 text-xs">{p.date}</td>
                            <td className="px-3 py-2 text-xs font-medium">{p.student}</td>
                            <td className="px-3 py-2 text-xs">{p.class}</td>
                            <td className="px-3 py-2 text-xs font-mono">{p.invoiceNo}</td>
                            <td className="px-3 py-2 text-xs font-semibold text-emerald-600">{p.amount}</td>
                            <td className="px-3 py-2 text-xs">{p.gateway}</td>
                            <td className="px-3 py-2 text-xs font-mono text-muted-foreground truncate max-w-[120px]">{p.reference}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(feeReport.payments?.length || 0) > 50 && (
                      <p className="text-xs text-center py-2 text-muted-foreground">Showing 50 of {feeReport.payments.length}. Export CSV for full data.</p>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Attendance Report */}
        <TabsContent value="attendance" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Attendance Report</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4 flex-wrap items-end">
                <div className="space-y-1.5">
                  <Label>Term</Label>
                  <Select onValueChange={setAttTermId}>
                    <SelectTrigger className="w-48"><SelectValue placeholder="Select term" /></SelectTrigger>
                    <SelectContent>
                      {(terms?.data || terms || []).map((t: any) => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={() => refetchAtt()} disabled={!attTermId || attLoading}>
                  {attLoading ? 'Generating...' : 'Generate Report'}
                </Button>
                {attReport && (
                  <Button variant="outline" onClick={handleExportAttendance}>
                    <Download className="w-4 h-4 mr-2" />Export CSV
                  </Button>
                )}
              </div>

              {attReport && (
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/30">
                      <tr>
                        {['Student', 'Class', 'Total Days', 'Present', 'Absent', 'Late', 'Rate'].map((h) => (
                          <th key={h} className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {(attReport.summary || []).map((s: any, i: number) => (
                        <tr key={i} className="hover:bg-muted/20">
                          <td className="px-3 py-2 text-sm font-medium">{s.name}</td>
                          <td className="px-3 py-2 text-xs">{s.class}</td>
                          <td className="px-3 py-2 text-xs">{s.total}</td>
                          <td className="px-3 py-2 text-xs text-emerald-600">{s.present}</td>
                          <td className="px-3 py-2 text-xs text-red-600">{s.absent}</td>
                          <td className="px-3 py-2 text-xs text-amber-600">{s.late}</td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-muted rounded-full h-1.5">
                                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${s.rate}%` }} />
                              </div>
                              <span className="text-xs font-medium">{s.rate}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
