'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { Package, Plus, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';

export default function ExpensesPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [paymentMethod, setPaymentMethod] = useState('');
  const { user, hasPermission } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['expenses'],
    queryFn: () => api.get<any>('/v1/finance/expenses'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/finance/expenses', { title, amount: Number(amount), description, date, paymentMethod }),
    onSuccess: () => {
      toast.success('Expense recorded');
      qc.invalidateQueries({ queryKey: ['expenses'] });
      setCreateOpen(false);
      setTitle(''); setAmount(''); setDescription(''); setPaymentMethod('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const expenses = data?.data || [];
  const totalAmount = expenses.reduce((s: number, e: any) => s + Number(e.amount), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="section-title">Expenses</h1><p className="section-subtitle">Track and manage school expenditures</p></div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="w-4 h-4 mr-2" />Export</Button>
          {hasPermission('finance:expenses:CREATE') && (
            <Button size="sm" onClick={() => setCreateOpen(true)}><Plus className="w-4 h-4 mr-2" />Record Expense</Button>
          )}
        </div>
      </div>

      <Card className="shadow-card"><CardContent className="pt-4 pb-4">
        <p className="text-xs text-muted-foreground">Total Expenses</p>
        <p className="text-2xl font-bold text-red-600">{sym}{totalAmount.toLocaleString()}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{expenses.length} records</p>
      </CardContent></Card>

      <Card className="data-table-container shadow-card">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Title</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Payment Method</TableHead>
              <TableHead>Description</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {expenses.length === 0
              ? <TableRow><TableCell colSpan={5} className="text-center py-12 text-muted-foreground"><Package className="w-10 h-10 mx-auto mb-2 opacity-20" />No expenses recorded</TableCell></TableRow>
              : expenses.map((e: any) => (
                <TableRow key={e.id} className="hover:bg-muted/30">
                  <TableCell className="font-medium text-sm">{e.title}</TableCell>
                  <TableCell className="text-red-600 font-semibold">{sym}{Number(e.amount).toLocaleString()}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{format(new Date(e.date), 'dd MMM yyyy')}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs">{e.paymentMethod || 'N/A'}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground truncate max-w-[200px]">{e.description || '—'}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Record Expense</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Title *</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Generator Fuel" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount ({sym}) *</Label><Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Date</Label><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
            </div>
            <div className="space-y-1.5"><Label>Payment Method</Label><Input value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} placeholder="Cash, Transfer..." /></div>
            <div className="space-y-1.5"><Label>Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!title || !amount || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Saving...' : 'Record Expense'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
