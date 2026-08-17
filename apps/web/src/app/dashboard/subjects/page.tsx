'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';

export default function SubjectsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [isElective, setIsElective] = useState(false);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({ queryKey: ['subjects'], queryFn: () => api.get<any>('/v1/subjects') });
  const { data: departments } = useQuery({ queryKey: ['departments'], queryFn: () => api.get<any>('/v1/schools/departments'), enabled: createOpen });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/subjects', { name, code, departmentId: departmentId || undefined, isElective }),
    onSuccess: () => { toast.success('Subject created'); qc.invalidateQueries({ queryKey: ['subjects'] }); setCreateOpen(false); setName(''); setCode(''); },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const subjects = data?.data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="section-title">Subjects</h1><p className="section-subtitle">Manage academic subjects and curriculum</p></div>
        {hasPermission('subjects:subjects:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}><Plus className="w-4 h-4 mr-2" />Add Subject</Button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4"><p className="text-2xl font-bold">{subjects.length}</p><p className="text-xs text-muted-foreground">Total Subjects</p></CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4"><p className="text-2xl font-bold">{subjects.filter((s: any) => s.isElective).length}</p><p className="text-xs text-muted-foreground">Electives</p></CardContent></Card>
      </div>
      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader><TableRow className="bg-muted/30"><TableHead>Subject</TableHead><TableHead>Code</TableHead><TableHead>Department</TableHead><TableHead>Classes</TableHead><TableHead>Type</TableHead></TableRow></TableHeader>
          <TableBody>
            {isLoading ? Array.from({length:6}).map((_,i) => <TableRow key={i}>{Array.from({length:5}).map((_,j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>)
              : subjects.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center py-12 text-muted-foreground"><BookOpen className="w-10 h-10 mx-auto mb-2 opacity-20" />No subjects yet</TableCell></TableRow>
              : subjects.map((s: any) => (
                <TableRow key={s.id} className="hover:bg-muted/30">
                  <TableCell className="font-medium text-sm">{s.name}</TableCell>
                  <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{s.code || '—'}</code></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.department?.name || '—'}</TableCell>
                  <TableCell className="text-sm">{s._count?.classSubjects || 0}</TableCell>
                  <TableCell><Badge variant={s.isElective ? 'secondary' : 'outline'} className="text-xs">{s.isElective ? 'Elective' : 'Core'}</Badge></TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Add Subject</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Mathematics" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Code</Label><Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="MTH" /></div>
              <div className="space-y-1.5"><Label>Department</Label>
                <Select onValueChange={setDepartmentId}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>{(departments?.data || departments || []).map((d: any) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center gap-3"><Switch checked={isElective} onCheckedChange={setIsElective} /><Label>Is Elective Subject</Label></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!name || createMutation.isPending} onClick={() => createMutation.mutate()}>{createMutation.isPending ? 'Creating...' : 'Create Subject'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
