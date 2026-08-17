'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';

interface LineItem { name: string; amount: number; discount: number }

interface Props { open: boolean; onClose: () => void }

export function CreateInvoiceDialog({ open, onClose }: Props) {
  const [studentId, setStudentId] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [feeStructureId, setFeeStructureId] = useState('');
  const [termId, setTermId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [items, setItems] = useState<LineItem[]>([{ name: '', amount: 0, discount: 0 }]);
  const { user } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const qc = useQueryClient();

  const { data: studentsData } = useQuery({
    queryKey: ['students-search', studentSearch],
    queryFn: () => api.get<any>('/v1/students', { search: studentSearch, limit: 20 }),
    enabled: open && studentSearch.length > 1,
  });

  const { data: feeStructures } = useQuery({
    queryKey: ['fee-structures'],
    queryFn: () => api.get<any>('/v1/finance/fee-structures'),
    enabled: open,
  });

  const { data: terms } = useQuery({
    queryKey: ['terms'],
    queryFn: () => api.get<any>('/v1/schools/terms'),
    enabled: open,
  });

  const loadStructure = async (id: string) => {
    setFeeStructureId(id);
    const structures = feeStructures?.data || feeStructures || [];
    const found = structures.find((s: any) => s.id === id);
    if (found?.items) {
      setItems(found.items.map((i: any) => ({ name: i.name, amount: Number(i.amount), discount: 0 })));
    }
  };

  const addItem = () => setItems((p) => [...p, { name: '', amount: 0, discount: 0 }]);
  const removeItem = (i: number) => setItems((p) => p.filter((_, idx) => idx !== i));
  const updateItem = (i: number, field: keyof LineItem, value: any) =>
    setItems((p) => p.map((item, idx) => idx === i ? { ...item, [field]: value } : item));

  const total = items.reduce((s, i) => s + (i.amount - i.discount), 0);

  const mutation = useMutation({
    mutationFn: () =>
      api.post('/v1/finance/invoices', {
        studentId,
        feeStructureId: feeStructureId || undefined,
        termId: termId || undefined,
        dueDate: dueDate || undefined,
        items: items.filter((i) => i.name && i.amount > 0),
      }),
    onSuccess: () => {
      toast.success('Invoice created successfully');
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['finance-dashboard'] });
      setStudentId(''); setFeeStructureId(''); setTermId('');
      setItems([{ name: '', amount: 0, discount: 0 }]);
      onClose();
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to create invoice'),
  });

  const students = studentsData?.data || [];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Invoice</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Student */}
          <div className="space-y-1.5">
            <Label>Student *</Label>
            <Input
              placeholder="Search student by name or admission no..."
              value={studentSearch}
              onChange={(e) => setStudentSearch(e.target.value)}
            />
            {students.length > 0 && !studentId && (
              <div className="border rounded-lg max-h-40 overflow-y-auto">
                {students.map((s: any) => (
                  <button
                    key={s.id}
                    type="button"
                    className="w-full text-left px-3 py-2 hover:bg-muted text-sm flex items-center gap-2"
                    onClick={() => {
                      setStudentId(s.id);
                      setStudentSearch(`${s.user.firstName} ${s.user.lastName} (${s.admissionNo})`);
                    }}
                  >
                    <span className="font-medium">{s.user.firstName} {s.user.lastName}</span>
                    <span className="text-muted-foreground font-mono text-xs">{s.admissionNo}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Fee Structure */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Fee Structure (optional)</Label>
              <Select onValueChange={loadStructure}>
                <SelectTrigger><SelectValue placeholder="Select or enter manually" /></SelectTrigger>
                <SelectContent>
                  {(feeStructures?.data || feeStructures || []).map((fs: any) => (
                    <SelectItem key={fs.id} value={fs.id}>{fs.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Term (optional)</Label>
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

          <div className="space-y-1.5">
            <Label>Due Date</Label>
            <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>

          {/* Line Items */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Fee Items *</Label>
              <Button type="button" variant="ghost" size="sm" onClick={addItem}>
                <Plus className="w-3.5 h-3.5 mr-1" /> Add Item
              </Button>
            </div>
            {items.map((item, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <Input
                  className="col-span-5 text-sm"
                  placeholder="Description"
                  value={item.name}
                  onChange={(e) => updateItem(i, 'name', e.target.value)}
                />
                <div className="col-span-3 relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">{sym}</span>
                  <Input
                    type="number"
                    className="pl-5 text-sm"
                    placeholder="Amount"
                    value={item.amount || ''}
                    onChange={(e) => updateItem(i, 'amount', parseFloat(e.target.value) || 0)}
                  />
                </div>
                <div className="col-span-3 relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">{sym}</span>
                  <Input
                    type="number"
                    className="pl-5 text-sm"
                    placeholder="Discount"
                    value={item.discount || ''}
                    onChange={(e) => updateItem(i, 'discount', parseFloat(e.target.value) || 0)}
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="col-span-1 w-7 h-7"
                  onClick={() => removeItem(i)}
                  disabled={items.length === 1}
                >
                  <Trash2 className="w-3.5 h-3.5 text-destructive" />
                </Button>
              </div>
            ))}

            <div className="flex justify-between pt-2 border-t font-semibold text-sm">
              <span>Total</span>
              <span>{sym}{total.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!studentId || items.every((i) => !i.name) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Invoice
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
