'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, CreditCard } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const schema = z.object({
  amount: z.number().positive('Amount must be positive'),
  gateway: z.string().min(1, 'Select a payment method'),
  gatewayRef: z.string().optional(),
  currency: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  open: boolean;
  invoice: any;
  onClose: () => void;
}

export function RecordPaymentDialog({ open, invoice, onClose }: Props) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const sym = user?.school?.currencySymbol || '₦';

  const { data: gateways } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => api.get<any>('/v1/finance/gateways'),
    enabled: open,
  });

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: user?.school?.currency || 'NGN' },
  });

  const balance = invoice
    ? Number(invoice.totalAmount) - Number(invoice.discountAmount) - Number(invoice.paidAmount)
    : 0;

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      api.post(`/v1/finance/invoices/${invoice.id}/payments`, data),
    onSuccess: () => {
      toast.success('Payment recorded successfully');
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['finance-dashboard'] });
      form.reset();
      onClose();
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to record payment'),
  });

  const onSubmit = (data: FormData) => mutation.mutate(data);

  const enabledGateways = (gateways || []).filter((g: any) => g.isEnabled);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" /> Record Payment
          </DialogTitle>
        </DialogHeader>

        {invoice && (
          <div className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Invoice</span>
              <span className="font-mono font-medium">{invoice.invoiceNo}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Student</span>
              <span className="font-medium">
                {invoice.student?.user?.firstName} {invoice.student?.user?.lastName}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Amount</span>
              <span className="font-medium">{sym}{Number(invoice.totalAmount).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Amount Paid</span>
              <span className="text-emerald-600 font-medium">{sym}{Number(invoice.paidAmount).toLocaleString()}</span>
            </div>
            <div className="flex justify-between border-t pt-2">
              <span className="font-semibold">Outstanding Balance</span>
              <span className={cn('font-bold text-base', balance > 0 ? 'text-red-600' : 'text-emerald-600')}>
                {sym}{balance.toLocaleString()}
              </span>
            </div>
          </div>
        )}

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Payment Amount *</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-medium">{sym}</span>
              <Input
                type="number"
                step="0.01"
                max={balance}
                className="pl-7"
                placeholder={balance.toString()}
                {...form.register('amount', { valueAsNumber: true })}
              />
            </div>
            {form.formState.errors.amount && (
              <p className="text-xs text-destructive">{form.formState.errors.amount.message}</p>
            )}
            <div className="flex gap-2">
              {[0.25, 0.5, 0.75, 1].map((frac) => (
                <Button
                  key={frac}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs h-7 flex-1"
                  onClick={() => form.setValue('amount', Math.round(balance * frac * 100) / 100)}
                >
                  {frac === 1 ? 'Full' : `${frac * 100}%`}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Payment Method *</Label>
            <Select onValueChange={(v) => form.setValue('gateway', v)}>
              <SelectTrigger>
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent>
                {/* Always show manual/cash */}
                <SelectItem value="CASH">Cash</SelectItem>
                <SelectItem value="BANK_TRANSFER">Bank Transfer</SelectItem>
                <SelectItem value="MANUAL">Manual / Cheque</SelectItem>
                {enabledGateways.map((g: any) => (
                  <SelectItem key={g.gateway} value={g.gateway}>
                    {g.displayName || g.gateway}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.gateway && (
              <p className="text-xs text-destructive">{form.formState.errors.gateway.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Reference / Transaction ID</Label>
            <Input
              placeholder="Optional reference number"
              {...form.register('gatewayRef')}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending || balance <= 0}>
              {mutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Record Payment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
