'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Calendar, Plus, Check, X, Clock, Filter, Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const STATUS_STYLES: Record<string, string> = {
  PENDING: 'badge-warning',
  APPROVED: 'badge-success',
  REJECTED: 'badge-danger',
  CANCELLED: 'badge-neutral',
};

export default function LeavePage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [approveDialog, setApproveDialog] = useState<{ id: string; action: 'APPROVED' | 'REJECTED' } | null>(null);
  const [remarks, setRemarks] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['leave-records', statusFilter],
    queryFn: () => api.get<any>('/v1/hr/leave', { status: statusFilter || undefined }),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.put(`/v1/hr/leave/${id}/approve`, { status, remarks }),
    onSuccess: () => {
      toast.success('Leave request updated');
      qc.invalidateQueries({ queryKey: ['leave-records'] });
      setApproveDialog(null);
      setRemarks('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const records = data?.data || [];
  const meta = data?.meta;

  const pending = records.filter((r: any) => r.status === 'PENDING').length;
  const approved = records.filter((r: any) => r.status === 'APPROVED').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Leave Management</h1>
          <p className="section-subtitle">Manage staff leave requests</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="w-4 h-4 mr-2" />Export</Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />New Request
          </Button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Pending', value: pending, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
          { label: 'Approved', value: approved, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
          { label: 'Total This Month', value: records.length, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
        ].map((s) => (
          <Card key={s.label} className="shadow-card">
            <CardContent className="pt-4 pb-4">
              <div className={cn('inline-flex p-2 rounded-lg mb-2', s.bg)}>
                <Calendar className={cn('w-4 h-4', s.color)} />
              </div>
              <p className={cn('text-2xl font-bold', s.color)}>{s.value}</p>
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-3">
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="APPROVED">Approved</SelectItem>
            <SelectItem value="REJECTED">Rejected</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Staff Member</TableHead>
              <TableHead>Leave Type</TableHead>
              <TableHead>From</TableHead>
              <TableHead>To</TableHead>
              <TableHead>Days</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Status</TableHead>
              {hasPermission('hr:leave:APPROVE') && <TableHead>Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>{Array.from({ length: 8 }).map((_, j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>
                ))
              : records.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    <Calendar className="w-10 h-10 mx-auto mb-2 opacity-20" />
                    No leave records found
                  </TableCell>
                </TableRow>
              )
              : records.map((r: any) => (
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
                    <TableCell><Badge variant="outline" className="text-xs">{r.type}</Badge></TableCell>
                    <TableCell className="text-sm">{format(new Date(r.startDate), 'dd MMM yyyy')}</TableCell>
                    <TableCell className="text-sm">{format(new Date(r.endDate), 'dd MMM yyyy')}</TableCell>
                    <TableCell className="text-sm font-medium">{r.days}</TableCell>
                    <TableCell className="text-sm max-w-[200px] truncate">{r.reason}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={cn('text-xs', STATUS_STYLES[r.status])}>
                        {r.status}
                      </Badge>
                    </TableCell>
                    {hasPermission('hr:leave:APPROVE') && (
                      <TableCell>
                        {r.status === 'PENDING' && (
                          <div className="flex gap-1">
                            <Button
                              size="sm" variant="ghost"
                              className="h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                              onClick={() => setApproveDialog({ id: r.id, action: 'APPROVED' })}
                            >
                              <Check className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              className="h-7 w-7 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => setApproveDialog({ id: r.id, action: 'REJECTED' })}
                            >
                              <X className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </Card>

      {/* Approve/Reject Dialog */}
      <Dialog open={!!approveDialog} onOpenChange={() => setApproveDialog(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {approveDialog?.action === 'APPROVED' ? '✅ Approve' : '❌ Reject'} Leave Request
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Label>Remarks (optional)</Label>
            <Textarea
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Add a remark for the staff member..."
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveDialog(null)}>Cancel</Button>
            <Button
              variant={approveDialog?.action === 'APPROVED' ? 'default' : 'destructive'}
              disabled={approveMutation.isPending}
              onClick={() => approveDialog && approveMutation.mutate({ id: approveDialog.id, status: approveDialog.action })}
            >
              {approveMutation.isPending ? 'Processing...' : approveDialog?.action === 'APPROVED' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
