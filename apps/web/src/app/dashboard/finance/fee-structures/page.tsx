'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Cog, Plus, Trash2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';

interface Item { name: string; amount: number; isOptional: boolean }

export default function FeeStructuresPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [academicYearId, setAcademicYearId] = useState('');
  const [items, setItems] = useState<Item[]>([{ name: '', amount: 0, isOptional: false }]);
  const { hasPermission, user } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const qc = useQueryClient();

  const { data: structures, isLoading } = useQuery({
    queryKey: ['fee-structures'],
    queryFn: () => api.get<any>('/v1/finance/fee-structures'),
  });

  const { data: academicYears } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => api.get<any>('/v1/schools/academic-years'),
    enabled: createOpen,
  });

  const { data: classes } = useQuery({
    queryKey: ['classes-list'],
    queryFn: () => api.get<any>('/v1/classes'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/finance/fee-structures', {
      name, academicYearId, items: items.filter((i) => i.name && i.amount > 0),
    }),
    onSuccess: () => {
      toast.success('Fee structure created');
      qc.invalidateQueries({ queryKey: ['fee-structures'] });
      setCreateOpen(false);
      setName(''); setItems([{ name: '', amount: 0, isOptional: false }]);
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const bulkGenMutation = useMutation({
    mutationFn: ({ feeStructureId, classRoomId, academicYearId }: any) =>
      api.post('/v1/finance/invoices/bulk-generate', { feeStructureId, classRoomId, academicYearId }),
    onSuccess: (data: any) => {
      toast.success(`Generated ${data.created} invoices (${data.skipped} skipped)`);
      qc.invalidateQueries({ queryKey: ['invoices'] });
    },
    onError: () => toast.error('Bulk generation failed'),
  });

  const list = structures?.data || structures || [];

  const addItem = () => setItems((p) => [...p, { name: '', amount: 0, isOptional: false }]);
  const removeItem = (i: number) => setItems((p) => p.filter((_, idx) => idx !== i));
  const updateItem = (i: number, field: keyof Item, value: any) =>
    setItems((p) => p.map((item, idx) => idx === i ? { ...item, [field]: value } : item));

  const total = items.reduce((s, i) => s + (i.amount || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Fee Structures</h1>
          <p className="section-subtitle">Define fee templates and generate invoices in bulk</p>
        </div>
        {hasPermission('finance:fee-structures:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />New Fee Structure
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {list.length === 0 && !isLoading && (
          <Card className="col-span-full"><CardContent className="py-16 text-center text-muted-foreground">
            <Cog className="w-12 h-12 mx-auto mb-3 opacity-20" />No fee structures created yet
          </CardContent></Card>
        )}
        {list.map((fs: any) => (
          <Card key={fs.id} className="shadow-card">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{fs.name}</CardTitle>
                <Badge variant="outline">{fs.academicYear?.name}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-1.5 mb-3">
                {fs.items?.map((item: any) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{item.name} {item.isOptional && <Badge variant="secondary" className="text-xs ml-1">Optional</Badge>}</span>
                    <span className="font-medium">{sym}{Number(item.amount).toLocaleString()}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-between pt-2 border-t font-semibold text-sm mb-3">
                <span>Total</span>
                <span>{sym}{fs.items?.reduce((s: number, i: any) => s + Number(i.amount), 0).toLocaleString()}</span>
              </div>

              {hasPermission('finance:invoices:CREATE') && (
                <BulkGenerateButton
                  feeStructureId={fs.id}
                  academicYearId={fs.academicYearId}
                  classes={classes?.data || classes || []}
                  onGenerate={(classRoomId) => bulkGenMutation.mutate({ feeStructureId: fs.id, classRoomId, academicYearId: fs.academicYearId })}
                  loading={bulkGenMutation.isPending}
                />
              )}

              <p className="text-xs text-muted-foreground mt-2">{fs._count?.invoices || 0} invoices generated</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>New Fee Structure</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Name *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. SS2 Science - 2nd Term" />
            </div>
            <div className="space-y-1.5">
              <Label>Academic Year *</Label>
              <Select onValueChange={setAcademicYearId}>
                <SelectTrigger><SelectValue placeholder="Select year" /></SelectTrigger>
                <SelectContent>
                  {(academicYears?.data || academicYears || []).map((y: any) => (
                    <SelectItem key={y.id} value={y.id}>{y.name} {y.isCurrent ? '(Current)' : ''}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Fee Items</Label>
                <Button type="button" variant="ghost" size="sm" onClick={addItem}><Plus className="w-3.5 h-3.5 mr-1" />Add</Button>
              </div>
              {items.map((item, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input className="flex-1 text-sm" placeholder="e.g. Tuition Fee" value={item.name} onChange={(e) => updateItem(i, 'name', e.target.value)} />
                  <div className="relative w-28">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">{sym}</span>
                    <Input className="pl-5 text-sm" type="number" value={item.amount || ''} onChange={(e) => updateItem(i, 'amount', parseFloat(e.target.value) || 0)} />
                  </div>
                  <Switch checked={item.isOptional} onCheckedChange={(v) => updateItem(i, 'isOptional', v)} />
                  <Button type="button" variant="ghost" size="icon" className="w-7 h-7" onClick={() => removeItem(i)} disabled={items.length === 1}>
                    <Trash2 className="w-3.5 h-3.5 text-destructive" />
                  </Button>
                </div>
              ))}
              <div className="flex justify-between pt-2 border-t font-semibold text-sm">
                <span>Total</span><span>{sym}{total.toLocaleString()}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!name || !academicYearId || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Fee Structure'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function BulkGenerateButton({ feeStructureId, classes, onGenerate, loading }: any) {
  const [classRoomId, setClassRoomId] = useState('');
  return (
    <div className="flex gap-2">
      <Select onValueChange={setClassRoomId}>
        <SelectTrigger className="flex-1 h-8 text-xs"><SelectValue placeholder="Select class to generate invoices" /></SelectTrigger>
        <SelectContent>
          {classes.map((c: any) => <SelectItem key={c.id} value={c.id}>{c.name} {c.section || ''}</SelectItem>)}
        </SelectContent>
      </Select>
      <Button size="sm" variant="outline" className="h-8 text-xs" disabled={!classRoomId || loading} onClick={() => onGenerate(classRoomId)}>
        <FileText className="w-3.5 h-3.5 mr-1" />Generate
      </Button>
    </div>
  );
}
