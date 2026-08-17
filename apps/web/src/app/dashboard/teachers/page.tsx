'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  GraduationCap, Plus, Search, Download, MoreHorizontal,
  Eye, Edit, Mail, Phone, Users, BookOpen, Filter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
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
import { CreateStaffDialog } from '@/components/hr/create-staff-dialog';

export default function TeachersPage() {
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const { hasPermission } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ['teachers', { search, deptFilter, page }],
    queryFn: () => api.get<any>('/v1/hr/staff', {
      search,
      departmentId: deptFilter || undefined,
      page,
      limit: 20,
    }),
    placeholderData: (p) => p,
  });

  const { data: stats } = useQuery({
    queryKey: ['hr-stats'],
    queryFn: () => api.get<any>('/v1/hr/stats'),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<any>('/v1/schools/departments'),
  });

  const staff = data?.data || [];
  const meta = data?.meta;

  const statCards = [
    { label: 'Total Staff', value: stats?.total || 0, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
    { label: 'Active', value: stats?.active || 0, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: 'On Leave', value: stats?.onLeave || 0, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
    { label: 'Departments', value: (departments?.data || departments || []).length, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-950/30' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Staff & Teachers</h1>
          <p className="section-subtitle">Manage all school staff members</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="w-4 h-4 mr-2" />Export</Button>
          {hasPermission('hr:staff:CREATE') && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />Add Staff
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <Card key={s.label} className="shadow-card">
            <CardContent className="pt-4 pb-4">
              <div className={`inline-flex p-2 rounded-lg ${s.bg} mb-2`}>
                <GraduationCap className={`w-4 h-4 ${s.color}`} />
              </div>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search staff..." className="pl-9" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <Select value={deptFilter} onValueChange={(v) => { setDeptFilter(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {(departments?.data || departments || []).map((d: any) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>#</TableHead>
              <TableHead>Staff Member</TableHead>
              <TableHead>Staff ID</TableHead>
              <TableHead>Position</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : staff.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    <GraduationCap className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p className="font-medium">No staff found</p>
                  </TableCell>
                </TableRow>
              )
              : staff.map((s: any, idx: number) => (
                  <TableRow key={s.id} className="hover:bg-muted/30">
                    <TableCell className="text-muted-foreground text-sm">{(page - 1) * 20 + idx + 1}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarImage src={s.user?.avatar} />
                          <AvatarFallback className="text-xs bg-primary/10 text-primary">
                            {s.user?.firstName?.[0]}{s.user?.lastName?.[0]}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-sm">{s.user?.firstName} {s.user?.lastName}</p>
                          <p className="text-xs text-muted-foreground">{s.user?.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell><Badge variant="outline" className="font-mono text-xs">{s.staffId}</Badge></TableCell>
                    <TableCell className="text-sm">{s.position || '—'}</TableCell>
                    <TableCell className="text-sm">{s.department?.name || '—'}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">{s.employmentType}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={s.employmentStatus === 'ACTIVE' ? 'badge-success' : 'badge-neutral'} variant="secondary">
                        {s.employmentStatus}
                      </Badge>
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
                            <Link href={`/dashboard/hr/staff/${s.id}`}>
                              <Eye className="w-4 h-4 mr-2" />View Profile
                            </Link>
                          </DropdownMenuItem>
                          {hasPermission('hr:staff:UPDATE') && (
                            <DropdownMenuItem asChild>
                              <Link href={`/dashboard/hr/staff/${s.id}/edit`}>
                                <Edit className="w-4 h-4 mr-2" />Edit
                              </Link>
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem>
                            <Mail className="w-4 h-4 mr-2" />Send Message
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
        {meta && meta.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <p className="text-sm text-muted-foreground">
              Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, meta.total)} of {meta.total}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <Button variant="outline" size="sm" disabled={page >= meta.totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Card>

      <CreateStaffDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
