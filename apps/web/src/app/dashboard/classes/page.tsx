'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Building2, Plus, Users, BookOpen, Eye, Edit, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function ClassesPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [className, setClassName] = useState('');
  const [section, setSection] = useState('');
  const [capacity, setCapacity] = useState(35);
  const [level, setLevel] = useState<number | ''>('');
  const [room, setRoom] = useState('');
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['classes'],
    queryFn: () => api.get<any>('/v1/classes'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/classes', { name: className, section, capacity, level: level || undefined, room }),
    onSuccess: () => {
      toast.success('Class created');
      qc.invalidateQueries({ queryKey: ['classes'] });
      setCreateOpen(false);
      setClassName(''); setSection(''); setCapacity(35); setLevel(''); setRoom('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const classes = data?.data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Classes</h1>
          <p className="section-subtitle">Manage classrooms and enrollment</p>
        </div>
        {hasPermission('classes:classes:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />Add Class
          </Button>
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold">{classes.length}</p>
          <p className="text-xs text-muted-foreground">Total Classes</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold">{classes.reduce((s: number, c: any) => s + (c._count?.enrollments || 0), 0)}</p>
          <p className="text-xs text-muted-foreground">Total Students</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <p className="text-2xl font-bold">{classes.reduce((s: number, c: any) => s + (c._count?.subjects || 0), 0)}</p>
          <p className="text-xs text-muted-foreground">Subject Assignments</p>
        </CardContent></Card>
      </div>

      {/* Grid of classes */}
      {isLoading
        ? <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-36" />)}</div>
        : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {classes.map((cls: any) => (
              <Card key={cls.id} className="shadow-card hover:border-primary/40 transition-colors">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                      <Building2 className="w-5 h-5 text-blue-600" />
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="w-7 h-7">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/classes/${cls.id}`}><Eye className="w-4 h-4 mr-2" />View Details</Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`/dashboard/classes/${cls.id}/edit`}><Edit className="w-4 h-4 mr-2" />Edit</Link>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <h3 className="font-bold text-lg">{cls.name}</h3>
                  {cls.section && <p className="text-sm text-muted-foreground">{cls.section}</p>}
                  <div className="flex gap-3 mt-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{cls._count?.enrollments || 0}/{cls.capacity}</span>
                    <span className="flex items-center gap-1"><BookOpen className="w-3.5 h-3.5" />{cls._count?.subjects || 0} subjects</span>
                  </div>
                  {cls.classTeacher && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Teacher: {cls.classTeacher?.staff?.user?.firstName} {cls.classTeacher?.staff?.user?.lastName}
                    </p>
                  )}
                  {cls.room && <p className="text-xs text-muted-foreground">Room: {cls.room}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Add Class</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Class Name *</Label>
              <Input value={className} onChange={(e) => setClassName(e.target.value)} placeholder="JSS 1" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Section/Stream</Label>
                <Input value={section} onChange={(e) => setSection(e.target.value)} placeholder="A, Science, Arts..." />
              </div>
              <div className="space-y-1.5">
                <Label>Level</Label>
                <Input type="number" value={level} onChange={(e) => setLevel(parseInt(e.target.value) || '')} placeholder="7" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Capacity</Label>
                <Input type="number" value={capacity} onChange={(e) => setCapacity(parseInt(e.target.value) || 35)} />
              </div>
              <div className="space-y-1.5">
                <Label>Room/Location</Label>
                <Input value={room} onChange={(e) => setRoom(e.target.value)} placeholder="Block A, Rm 12" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!className || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Class'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
