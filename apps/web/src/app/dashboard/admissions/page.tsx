'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  School, Plus, Eye, CheckCircle, XCircle, Clock,
  FileText, MoreHorizontal, Download, Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const STATUS_CONFIG: Record<string, { label: string; class: string }> = {
  DRAFT: { label: 'Draft', class: 'badge-neutral' },
  SUBMITTED: { label: 'Submitted', class: 'badge-info' },
  UNDER_REVIEW: { label: 'Under Review', class: 'badge-warning' },
  SHORTLISTED: { label: 'Shortlisted', class: 'badge-info' },
  INTERVIEW_SCHEDULED: { label: 'Interview', class: 'badge-warning' },
  ADMITTED: { label: 'Admitted', class: 'badge-success' },
  REJECTED: { label: 'Rejected', class: 'badge-danger' },
  WAITLISTED: { label: 'Waitlisted', class: 'badge-neutral' },
  WITHDRAWN: { label: 'Withdrawn', class: 'badge-neutral' },
};

export default function AdmissionsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['admissions', { search, statusFilter, page }],
    queryFn: () => api.get<any>('/v1/admissions', {
      search, status: statusFilter || undefined, page, limit: 20,
    }),
    placeholderData: (p) => p,
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.put(`/v1/admissions/${id}/status`, { status }),
    onSuccess: () => {
      toast.success('Application status updated');
      qc.invalidateQueries({ queryKey: ['admissions'] });
    },
    onError: () => toast.error('Failed to update status'),
  });

  const applications = data?.data || [];
  const meta = data?.meta;

  const statCards = [
    { label: 'Total', value: meta?.total || 0, status: null },
    { label: 'Pending Review', value: applications.filter((a: any) => ['SUBMITTED', 'UNDER_REVIEW'].includes(a.status)).length, status: 'SUBMITTED' },
    { label: 'Admitted', value: applications.filter((a: any) => a.status === 'ADMITTED').length, status: 'ADMITTED' },
    { label: 'Rejected', value: applications.filter((a: any) => a.status === 'REJECTED').length, status: 'REJECTED' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Admissions</h1>
          <p className="section-subtitle">Manage student applications and admissions</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="w-4 h-4 mr-2" />Export</Button>
          {hasPermission('admissions:admissions:CREATE') && (
            <Button size="sm">
              <Plus className="w-4 h-4 mr-2" />New Application
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <Card key={s.label} className="shadow-card cursor-pointer hover:border-primary/30 transition-colors"
            onClick={() => setStatusFilter(s.status || '')}>
            <CardContent className="pt-4 pb-4">
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search applications..." className="pl-9" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {Object.entries(STATUS_CONFIG).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Application No</TableHead>
              <TableHead>Applicant</TableHead>
              <TableHead>Applied Class</TableHead>
              <TableHead>Academic Year</TableHead>
              <TableHead>Applied Date</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>{Array.from({ length: 7 }).map((_, j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>
                ))
              : applications.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    <School className="w-12 h-12 mx-auto mb-2 opacity-20" />
                    <p className="font-medium">No applications found</p>
                  </TableCell>
                </TableRow>
              )
              : applications.map((app: any) => {
                  const cfg = STATUS_CONFIG[app.status] || { label: app.status, class: 'badge-neutral' };
                  return (
                    <TableRow key={app.id} className="hover:bg-muted/30">
                      <TableCell><Badge variant="outline" className="font-mono text-xs">{app.applicationNo}</Badge></TableCell>
                      <TableCell>
                        <p className="font-medium text-sm">
                          {app.student?.user?.firstName} {app.student?.user?.lastName}
                        </p>
                        <p className="text-xs text-muted-foreground">{app.student?.user?.email}</p>
                      </TableCell>
                      <TableCell className="text-sm">{app.appliedClass}</TableCell>
                      <TableCell className="text-sm">{app.academicYear}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(new Date(app.createdAt), 'dd MMM yyyy')}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={cn('text-xs', cfg.class)}>{cfg.label}</Badge>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="w-8 h-8">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem asChild>
                              <Link href={`/dashboard/admissions/${app.id}`}>
                                <Eye className="w-4 h-4 mr-2" />View Application
                              </Link>
                            </DropdownMenuItem>
                            {hasPermission('admissions:admissions:APPROVE') && app.status === 'SUBMITTED' && (
                              <>
                                <DropdownMenuItem onClick={() => updateStatus.mutate({ id: app.id, status: 'UNDER_REVIEW' })}>
                                  <Clock className="w-4 h-4 mr-2" />Mark Under Review
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => updateStatus.mutate({ id: app.id, status: 'ADMITTED' })}>
                                  <CheckCircle className="w-4 h-4 mr-2 text-emerald-600" />Admit Student
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  className="text-red-600 focus:text-red-600"
                                  onClick={() => updateStatus.mutate({ id: app.id, status: 'REJECTED' })}
                                >
                                  <XCircle className="w-4 h-4 mr-2" />Reject
                                </DropdownMenuItem>
                              </>
                            )}
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
            <p className="text-sm text-muted-foreground">Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, meta.total)} of {meta.total}</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <Button variant="outline" size="sm" disabled={page >= meta.totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
