'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { DollarSign, Download, Play, CheckCircle2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

export default function PayrollPage() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const { hasPermission, user } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const qc = useQueryClient();

  const { data: records, isLoading } = useQuery({
    queryKey: ['payroll', month, year],
    queryFn: () => api.get<any>('/v1/hr/payroll', { month, year }),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.post('/v1/hr/payroll/generate', { month, year }),
    onSuccess: (data: any) => {
      toast.success(`Generated payroll for ${data.generated} staff members`);
      qc.invalidateQueries({ queryKey: ['payroll', month, year] });
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to generate payroll'),
  });

  const list = records || [];
  const totalGross = list.reduce((s: number, r: any) => s + Number(r.grossSalary), 0);
  const totalNet = list.reduce((s: number, r: any) => s + Number(r.netSalary), 0);
  const totalDeductions = totalGross - totalNet;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Payroll</h1>
          <p className="section-subtitle">Manage staff salaries and payments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="w-4 h-4 mr-2" />Export</Button>
          {hasPermission('hr:payroll:CREATE') && (
            <Button size="sm" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
              <Play className="w-4 h-4 mr-2" />
              {generateMutation.isPending ? 'Generating...' : 'Generate Payroll'}
            </Button>
          )}
        </div>
      </div>

      {/* Period selector */}
      <div className="flex gap-3">
        <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            {MONTHS.map((m, i) => <SelectItem key={i} value={String(i + 1)}>{m}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[now.getFullYear(), now.getFullYear() - 1].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold">{sym}{totalGross.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">Total Gross</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold text-red-600">{sym}{totalDeductions.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">Total Deductions</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold text-emerald-600">{sym}{totalNet.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">Total Net Payable</p>
        </CardContent></Card>
      </div>

      {/* Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Staff</TableHead>
              <TableHead className="text-right">Basic Salary</TableHead>
              <TableHead className="text-right">Allowances</TableHead>
              <TableHead className="text-right">Deductions</TableHead>
              <TableHead className="text-right">Net Salary</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    <DollarSign className="w-10 h-10 mx-auto mb-2 opacity-20" />
                    <p>No payroll generated for {MONTHS[month - 1]} {year}</p>
                    {hasPermission('hr:payroll:CREATE') && (
                      <p className="text-xs mt-1">Click &quot;Generate Payroll&quot; to process salaries</p>
                    )}
                  </TableCell>
                </TableRow>
              )
              : list.map((r: any) => {
                  const allowances = Object.values(r.allowances || {}).reduce((a: number, b: any) => a + Number(b), 0);
                  const deductions = Object.values(r.deductions || {}).reduce((a: number, b: any) => a + Number(b), 0);
                  return (
                    <TableRow key={r.id} className="hover:bg-muted/30">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Avatar className="w-7 h-7">
                            <AvatarFallback className="text-xs bg-primary/10 text-primary">
                              {r.staff?.user?.firstName?.[0]}{r.staff?.user?.lastName?.[0]}
                            </AvatarFallback>
                          </Avatar>
                          <span className="text-sm font-medium">{r.staff?.user?.firstName} {r.staff?.user?.lastName}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-sm">{sym}{Number(r.basicSalary).toLocaleString()}</TableCell>
                      <TableCell className="text-right text-sm text-emerald-600">+{sym}{allowances.toLocaleString()}</TableCell>
                      <TableCell className="text-right text-sm text-red-600">-{sym}{deductions.toLocaleString()}</TableCell>
                      <TableCell className="text-right text-sm font-bold">{sym}{Number(r.netSalary).toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={cn('text-xs', r.status === 'COMPLETED' ? 'badge-success' : 'badge-warning')}>
                          {r.status === 'COMPLETED' ? <CheckCircle2 className="w-3 h-3 mr-1" /> : <Clock className="w-3 h-3 mr-1" />}
                          {r.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
