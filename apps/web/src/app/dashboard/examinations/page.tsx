'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Trophy, Plus, Eye, Edit, BarChart3, CheckCircle2,
  Clock, AlertCircle, FileText, MoreHorizontal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'badge-neutral',
  PUBLISHED: 'badge-info',
  ONGOING: 'badge-warning',
  COMPLETED: 'badge-success',
  RESULTS_PUBLISHED: 'badge-success',
  CANCELLED: 'badge-danger',
};

export default function ExaminationsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [examName, setExamName] = useState('');
  const [examType, setExamType] = useState('');
  const [termId, setTermId] = useState('');
  const [academicYearId, setAcademicYearId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [instructions, setInstructions] = useState('');
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['examinations'],
    queryFn: () => api.get<any>('/v1/examinations'),
  });

  const { data: terms } = useQuery({
    queryKey: ['terms'],
    queryFn: () => api.get<any>('/v1/schools/terms'),
    enabled: createOpen,
  });

  const { data: academicYears } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => api.get<any>('/v1/schools/academic-years'),
    enabled: createOpen,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/examinations', {
      name: examName, type: examType, termId, academicYearId,
      startDate, endDate, instructions,
    }),
    onSuccess: () => {
      toast.success('Examination created');
      qc.invalidateQueries({ queryKey: ['examinations'] });
      setCreateOpen(false);
      setExamName(''); setExamType(''); setTermId(''); setInstructions('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => api.put(`/v1/examinations/${id}/publish`, {}),
    onSuccess: () => { toast.success('Results published'); qc.invalidateQueries({ queryKey: ['examinations'] }); },
  });

  const exams = data?.data || data || [];

  const statCards = [
    { label: 'Total Exams', value: exams.length, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
    { label: 'Ongoing', value: exams.filter((e: any) => e.status === 'ONGOING').length, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
    { label: 'Completed', value: exams.filter((e: any) => e.status === 'COMPLETED').length, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: 'Results Published', value: exams.filter((e: any) => e.status === 'RESULTS_PUBLISHED').length, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-950/30' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Examinations</h1>
          <p className="section-subtitle">Manage exams and publish results</p>
        </div>
        {hasPermission('examinations:examinations:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />Create Examination
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <Card key={s.label} className="shadow-card">
            <CardContent className="pt-4 pb-4">
              <div className={cn('inline-flex p-2 rounded-lg mb-2', s.bg)}>
                <Trophy className={cn('w-4 h-4', s.color)} />
              </div>
              <p className={cn('text-2xl font-bold', s.color)}>{s.value}</p>
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Exams Table */}
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Examination</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Term</TableHead>
              <TableHead>Period</TableHead>
              <TableHead>Results</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>{Array.from({ length: 7 }).map((_, j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>
                ))
              : exams.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    <Trophy className="w-12 h-12 mx-auto mb-2 opacity-20" />
                    No examinations yet. Create your first one.
                  </TableCell>
                </TableRow>
              )
              : exams.map((exam: any) => (
                  <TableRow key={exam.id} className="hover:bg-muted/30">
                    <TableCell>
                      <p className="font-medium text-sm">{exam.name}</p>
                      {exam.instructions && <p className="text-xs text-muted-foreground truncate max-w-[200px]">{exam.instructions}</p>}
                    </TableCell>
                    <TableCell><Badge variant="outline" className="text-xs">{exam.type}</Badge></TableCell>
                    <TableCell className="text-sm">{exam.term?.name || '—'}</TableCell>
                    <TableCell className="text-sm">
                      {exam.startDate && exam.endDate
                        ? `${format(new Date(exam.startDate), 'dd MMM')} – ${format(new Date(exam.endDate), 'dd MMM yyyy')}`
                        : '—'}
                    </TableCell>
                    <TableCell className="text-sm">{exam._count?.results || 0} results</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={cn('text-xs', STATUS_STYLES[exam.status] || 'badge-neutral')}>
                        {exam.status}
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
                            <Link href={`/dashboard/examinations/${exam.id}`}>
                              <Eye className="w-4 h-4 mr-2" />View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link href={`/dashboard/examinations/${exam.id}/results`}>
                              <BarChart3 className="w-4 h-4 mr-2" />Enter Results
                            </Link>
                          </DropdownMenuItem>
                          {exam.status === 'COMPLETED' && hasPermission('examinations:examinations:UPDATE') && (
                            <DropdownMenuItem onClick={() => publishMutation.mutate(exam.id)}>
                              <CheckCircle2 className="w-4 h-4 mr-2" />Publish Results
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </Card>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Examination</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Examination Name *</Label>
              <Input value={examName} onChange={(e) => setExamName(e.target.value)} placeholder="Second Term Examination 2025" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Exam Type *</Label>
                <Select onValueChange={setExamType}>
                  <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MID_TERM">Mid Term</SelectItem>
                    <SelectItem value="FINAL_EXAM">Final Exam</SelectItem>
                    <SelectItem value="QUIZ">Quiz</SelectItem>
                    <SelectItem value="EXAM">Terminal Exam</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Term</Label>
                <Select onValueChange={setTermId}>
                  <SelectTrigger><SelectValue placeholder="Select term" /></SelectTrigger>
                  <SelectContent>
                    {(terms?.data || terms || []).map((t: any) => (
                      <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Start Date</Label>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>End Date</Label>
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Academic Year</Label>
              <Select onValueChange={setAcademicYearId}>
                <SelectTrigger><SelectValue placeholder="Select year" /></SelectTrigger>
                <SelectContent>
                  {(academicYears?.data || academicYears || []).map((y: any) => (
                    <SelectItem key={y.id} value={y.id}>{y.name} {y.isCurrent ? '(Current)' : ''}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Instructions</Label>
              <Textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={2} placeholder="Instructions for students..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!examName || !examType || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Examination'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
