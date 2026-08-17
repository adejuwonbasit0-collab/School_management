'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Plus, Search, Filter, Download, Upload, MoreHorizontal,
  Eye, Edit, Trash2, Users, UserCheck, UserX, GraduationCap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
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
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import { CreateStudentDialog } from '@/components/students/create-student-dialog';

export default function StudentsPage() {
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['students', { search, classFilter, page }],
    queryFn: () => api.get<any>('/v1/students', { search, classRoomId: classFilter, page, limit: 20 }),
    placeholderData: (prev) => prev,
  });

  const { data: classes } = useQuery({
    queryKey: ['classes-list'],
    queryFn: () => api.get<any>('/v1/classes'),
  });

  const { data: statsData } = useQuery({
    queryKey: ['students-stats'],
    queryFn: () => api.get<any>('/v1/students/stats'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/students/${id}`),
    onSuccess: () => {
      toast.success('Student archived');
      qc.invalidateQueries({ queryKey: ['students'] });
    },
    onError: () => toast.error('Failed to archive student'),
  });

  const students = data?.data || [];
  const meta = data?.meta;

  const statCards = [
    { label: 'Total Students', value: statsData?.totalStudents || 0, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
    { label: 'Enrolled', value: statsData?.activeEnrollments || 0, icon: UserCheck, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: 'Male', value: statsData?.genderStats?.find((g: any) => g.gender === 'MALE')?._count || 0, icon: GraduationCap, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-950/30' },
    { label: 'Female', value: statsData?.genderStats?.find((g: any) => g.gender === 'FEMALE')?._count || 0, icon: Users, color: 'text-pink-600', bg: 'bg-pink-50 dark:bg-pink-950/30' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Students</h1>
          <p className="section-subtitle">Manage all enrolled students</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Upload className="w-4 h-4 mr-2" /> Import
          </Button>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" /> Export
          </Button>
          {hasPermission('students:students:CREATE') && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-2" /> Add Student
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label} className="shadow-card">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${s.bg}`}>
                    <Icon className={`w-4 h-4 ${s.color}`} />
                  </div>
                  <div>
                    <p className="text-xl font-bold">{s.value.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, admission no..."
            className="pl-9"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <Select value={classFilter} onValueChange={(v) => { setClassFilter(v === 'all' ? '' : v); setPage(1); }}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by class" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Classes</SelectItem>
            {(classes?.data || classes || []).map((c: any) => (
              <SelectItem key={c.id} value={c.id}>{c.name} {c.section || ''}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-12">#</TableHead>
              <TableHead>Student</TableHead>
              <TableHead>Admission No</TableHead>
              <TableHead>Class</TableHead>
              <TableHead>Gender</TableHead>
              <TableHead>Parent</TableHead>
              <TableHead>Admission Date</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : students.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    <Users className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p className="font-medium">No students found</p>
                    <p className="text-sm mt-1">Add your first student to get started</p>
                  </TableCell>
                </TableRow>
              )
              : students.map((student: any, idx: number) => {
                const enrollment = student.enrollments?.[0];
                const primaryParent = student.parents?.find((p: any) => p.isPrimary) || student.parents?.[0];
                return (
                  <TableRow key={student.id} className="hover:bg-muted/30">
                    <TableCell className="text-muted-foreground text-sm">
                      {(page - 1) * 20 + idx + 1}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarImage src={student.user.avatar} />
                          <AvatarFallback className="text-xs bg-primary/10 text-primary">
                            {student.user.firstName[0]}{student.user.lastName[0]}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-sm">
                            {student.user.firstName} {student.user.lastName}
                          </p>
                          <p className="text-xs text-muted-foreground">{student.user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">{student.admissionNo}</Badge>
                    </TableCell>
                    <TableCell>
                      {enrollment ? (
                        <span className="text-sm">
                          {enrollment.classRoom?.name} {enrollment.classRoom?.section || ''}
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-xs">Not enrolled</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={student.user.gender === 'MALE' ? 'badge-info' : student.user.gender === 'FEMALE' ? 'badge-warning' : 'badge-neutral'}
                      >
                        {student.user.gender || 'N/A'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {primaryParent ? (
                        <div>
                          <p className="text-sm">{primaryParent.parent?.user?.firstName} {primaryParent.parent?.user?.lastName}</p>
                          <p className="text-xs text-muted-foreground">{primaryParent.relationship}</p>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {format(new Date(student.admissionDate), 'dd MMM yyyy')}
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
                            <Link href={`/dashboard/students/${student.id}`}>
                              <Eye className="w-4 h-4 mr-2" /> View Profile
                            </Link>
                          </DropdownMenuItem>
                          {hasPermission('students:students:UPDATE') && (
                            <DropdownMenuItem asChild>
                              <Link href={`/dashboard/students/${student.id}/edit`}>
                                <Edit className="w-4 h-4 mr-2" /> Edit
                              </Link>
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          {hasPermission('students:students:DELETE') && (
                            <DropdownMenuItem
                              className="text-red-600 focus:text-red-600"
                              onClick={() => {
                                if (confirm('Archive this student?')) {
                                  deleteMutation.mutate(student.id);
                                }
                              }}
                            >
                              <Trash2 className="w-4 h-4 mr-2" /> Archive
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
          </TableBody>
        </Table>

        {/* Pagination */}
        {meta && meta.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <p className="text-sm text-muted-foreground">
              Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, meta.total)} of {meta.total} students
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage((p) => p - 1)} disabled={page === 1}>
                Previous
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page >= meta.totalPages}>
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      <CreateStudentDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
