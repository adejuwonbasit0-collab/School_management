'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import api from '@/lib/api-client';
import toast from 'react-hot-toast';

const schema = z.object({
  firstName: z.string().min(1, 'Required'),
  lastName: z.string().min(1, 'Required'),
  email: z.string().email('Valid email required'),
  phone: z.string().optional(),
  gender: z.string().optional(),
  dateOfBirth: z.string().optional(),
  position: z.string().optional(),
  departmentId: z.string().optional(),
  employmentType: z.string().optional(),
  joiningDate: z.string().optional(),
  salary: z.number().optional(),
  qualification: z.string().optional(),
  bankName: z.string().optional(),
  bankAccountNo: z.string().optional(),
  bankAccountName: z.string().optional(),
  isTeacher: z.boolean().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props { open: boolean; onClose: () => void }

export function CreateStaffDialog({ open, onClose }: Props) {
  const qc = useQueryClient();
  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { isTeacher: false, employmentType: 'FULL_TIME' },
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<any>('/v1/schools/departments'),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) => api.post('/v1/hr/staff', data),
    onSuccess: () => {
      toast.success('Staff member created successfully');
      qc.invalidateQueries({ queryKey: ['teachers'] });
      qc.invalidateQueries({ queryKey: ['hr-stats'] });
      form.reset();
      onClose();
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to create staff'),
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Staff Member</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))}>
          <Tabs defaultValue="personal" className="mt-2">
            <TabsList className="grid grid-cols-3 w-full">
              <TabsTrigger value="personal">Personal</TabsTrigger>
              <TabsTrigger value="employment">Employment</TabsTrigger>
              <TabsTrigger value="banking">Banking</TabsTrigger>
            </TabsList>

            <TabsContent value="personal" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>First Name *</Label>
                  <Input {...form.register('firstName')} placeholder="Emeka" />
                  {form.formState.errors.firstName && <p className="text-xs text-destructive">{form.formState.errors.firstName.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <Label>Last Name *</Label>
                  <Input {...form.register('lastName')} placeholder="Adeyemi" />
                  {form.formState.errors.lastName && <p className="text-xs text-destructive">{form.formState.errors.lastName.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <Label>Email *</Label>
                  <Input {...form.register('email')} type="email" />
                  {form.formState.errors.email && <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <Label>Phone</Label>
                  <Input {...form.register('phone')} />
                </div>
                <div className="space-y-1.5">
                  <Label>Gender</Label>
                  <Select onValueChange={(v) => form.setValue('gender', v)}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MALE">Male</SelectItem>
                      <SelectItem value="FEMALE">Female</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Date of Birth</Label>
                  <Input type="date" {...form.register('dateOfBirth')} />
                </div>
                <div className="space-y-1.5 col-span-2">
                  <Label>Qualification</Label>
                  <Input {...form.register('qualification')} placeholder="B.Sc Mathematics, PGDE" />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="employment" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Position / Title</Label>
                  <Input {...form.register('position')} placeholder="Mathematics Teacher" />
                </div>
                <div className="space-y-1.5">
                  <Label>Department</Label>
                  <Select onValueChange={(v) => form.setValue('departmentId', v)}>
                    <SelectTrigger><SelectValue placeholder="Select department" /></SelectTrigger>
                    <SelectContent>
                      {(departments?.data || departments || []).map((d: any) => (
                        <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Employment Type</Label>
                  <Select defaultValue="FULL_TIME" onValueChange={(v) => form.setValue('employmentType', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="FULL_TIME">Full Time</SelectItem>
                      <SelectItem value="PART_TIME">Part Time</SelectItem>
                      <SelectItem value="CONTRACT">Contract</SelectItem>
                      <SelectItem value="INTERN">Intern</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Joining Date</Label>
                  <Input type="date" {...form.register('joiningDate')} />
                </div>
                <div className="space-y-1.5">
                  <Label>Monthly Salary (₦)</Label>
                  <Input type="number" {...form.register('salary', { valueAsNumber: true })} placeholder="120000" />
                </div>
                <div className="space-y-1.5 flex items-center gap-3 pt-6">
                  <Switch
                    checked={form.watch('isTeacher')}
                    onCheckedChange={(v) => form.setValue('isTeacher', v)}
                  />
                  <Label>Is a Teaching Staff</Label>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="banking" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Bank Name</Label>
                  <Input {...form.register('bankName')} placeholder="Zenith Bank" />
                </div>
                <div className="space-y-1.5">
                  <Label>Account Number</Label>
                  <Input {...form.register('bankAccountNo')} placeholder="0123456789" />
                </div>
                <div className="col-span-2 space-y-1.5">
                  <Label>Account Name</Label>
                  <Input {...form.register('bankAccountName')} placeholder="ADEYEMI EMEKA JOHN" />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Banking details are used for payroll processing and are stored securely.
              </p>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create Staff Member
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
