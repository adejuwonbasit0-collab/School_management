'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api-client';
import toast from 'react-hot-toast';

const schema = z.object({
  firstName: z.string().min(1, 'Required'),
  lastName: z.string().min(1, 'Required'),
  middleName: z.string().optional(),
  email: z.string().email('Valid email required'),
  phone: z.string().optional(),
  gender: z.enum(['MALE', 'FEMALE', 'OTHER']).optional(),
  dateOfBirth: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  bloodGroup: z.string().optional(),
  nationality: z.string().optional(),
  religion: z.string().optional(),
  classRoomId: z.string().optional(),
  academicYearId: z.string().optional(),
  rollNumber: z.string().optional(),
  admissionDate: z.string().optional(),
  medicalConditions: z.string().optional(),
  allergies: z.string().optional(),
  previousSchool: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface Parent {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  relationship: string;
  isPrimary: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CreateStudentDialog({ open, onClose }: Props) {
  const [parents, setParents] = useState<Parent[]>([{
    firstName: '', lastName: '', email: '', phone: '', relationship: 'Father', isPrimary: true,
  }]);
  const qc = useQueryClient();

  const form = useForm<FormData>({ resolver: zodResolver(schema) });

  const { data: classes } = useQuery({
    queryKey: ['classes-list'],
    queryFn: () => api.get<any>('/v1/classes'),
    enabled: open,
  });

  const { data: academicYears } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => api.get<any>('/v1/schools/academic-years'),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: (data: any) => api.post('/v1/students', data),
    onSuccess: () => {
      toast.success('Student created successfully');
      qc.invalidateQueries({ queryKey: ['students'] });
      qc.invalidateQueries({ queryKey: ['students-stats'] });
      form.reset();
      setParents([{ firstName: '', lastName: '', email: '', phone: '', relationship: 'Father', isPrimary: true }]);
      onClose();
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to create student'),
  });

  const onSubmit = (data: FormData) => {
    mutation.mutate({ ...data, parents: parents.filter((p) => p.firstName && p.lastName) });
  };

  const addParent = () => {
    setParents((p) => [...p, { firstName: '', lastName: '', email: '', phone: '', relationship: 'Mother', isPrimary: false }]);
  };

  const removeParent = (i: number) => setParents((p) => p.filter((_, idx) => idx !== i));

  const updateParent = (i: number, field: keyof Parent, value: any) => {
    setParents((prev) => prev.map((p, idx) => idx === i ? { ...p, [field]: value } : p));
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Student</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)}>
          <Tabs defaultValue="personal" className="mt-2">
            <TabsList className="grid grid-cols-4 w-full">
              <TabsTrigger value="personal">Personal</TabsTrigger>
              <TabsTrigger value="academic">Academic</TabsTrigger>
              <TabsTrigger value="parents">Parents</TabsTrigger>
              <TabsTrigger value="medical">Medical</TabsTrigger>
            </TabsList>

            {/* Personal Info */}
            <TabsContent value="personal" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>First Name *</Label>
                  <Input {...form.register('firstName')} placeholder="John" />
                  {form.formState.errors.firstName && (
                    <p className="text-xs text-destructive">{form.formState.errors.firstName.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label>Last Name *</Label>
                  <Input {...form.register('lastName')} placeholder="Doe" />
                  {form.formState.errors.lastName && (
                    <p className="text-xs text-destructive">{form.formState.errors.lastName.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label>Middle Name</Label>
                  <Input {...form.register('middleName')} placeholder="Optional" />
                </div>
                <div className="space-y-1.5">
                  <Label>Email *</Label>
                  <Input {...form.register('email')} type="email" placeholder="student@school.ng" />
                  {form.formState.errors.email && (
                    <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label>Phone</Label>
                  <Input {...form.register('phone')} placeholder="+234..." />
                </div>
                <div className="space-y-1.5">
                  <Label>Gender</Label>
                  <Select onValueChange={(v) => form.setValue('gender', v as any)}>
                    <SelectTrigger><SelectValue placeholder="Select gender" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MALE">Male</SelectItem>
                      <SelectItem value="FEMALE">Female</SelectItem>
                      <SelectItem value="OTHER">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Date of Birth</Label>
                  <Input {...form.register('dateOfBirth')} type="date" />
                </div>
                <div className="space-y-1.5">
                  <Label>Blood Group</Label>
                  <Select onValueChange={(v) => form.setValue('bloodGroup', v)}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      {['A_POSITIVE','A_NEGATIVE','B_POSITIVE','B_NEGATIVE','AB_POSITIVE','AB_NEGATIVE','O_POSITIVE','O_NEGATIVE'].map((bg) => (
                        <SelectItem key={bg} value={bg}>{bg.replace('_', ' ')}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <Label>Nationality</Label>
                  <Input {...form.register('nationality')} placeholder="Nigerian" />
                </div>
                <div className="space-y-1.5">
                  <Label>Religion</Label>
                  <Input {...form.register('religion')} placeholder="Christianity" />
                </div>
                <div className="space-y-1.5">
                  <Label>Previous School</Label>
                  <Input {...form.register('previousSchool')} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Address</Label>
                <Input {...form.register('address')} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>City</Label>
                  <Input {...form.register('city')} />
                </div>
                <div className="space-y-1.5">
                  <Label>State</Label>
                  <Input {...form.register('state')} />
                </div>
              </div>
            </TabsContent>

            {/* Academic */}
            <TabsContent value="academic" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Class</Label>
                  <Select onValueChange={(v) => form.setValue('classRoomId', v)}>
                    <SelectTrigger><SelectValue placeholder="Select class" /></SelectTrigger>
                    <SelectContent>
                      {(classes?.data || classes || []).map((c: any) => (
                        <SelectItem key={c.id} value={c.id}>{c.name} {c.section || ''}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Academic Year</Label>
                  <Select onValueChange={(v) => form.setValue('academicYearId', v)}>
                    <SelectTrigger><SelectValue placeholder="Select year" /></SelectTrigger>
                    <SelectContent>
                      {(academicYears?.data || academicYears || []).map((y: any) => (
                        <SelectItem key={y.id} value={y.id}>{y.name} {y.isCurrent ? '(Current)' : ''}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Roll Number</Label>
                  <Input {...form.register('rollNumber')} placeholder="Optional" />
                </div>
                <div className="space-y-1.5">
                  <Label>Admission Date</Label>
                  <Input {...form.register('admissionDate')} type="date" />
                </div>
              </div>
            </TabsContent>

            {/* Parents */}
            <TabsContent value="parents" className="space-y-4 mt-4">
              {parents.map((parent, i) => (
                <div key={i} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">Parent / Guardian {i + 1}</h4>
                    {i > 0 && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeParent(i)}>
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">First Name</Label>
                      <Input value={parent.firstName} onChange={(e) => updateParent(i, 'firstName', e.target.value)} placeholder="Jane" />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Last Name</Label>
                      <Input value={parent.lastName} onChange={(e) => updateParent(i, 'lastName', e.target.value)} placeholder="Doe" />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Email</Label>
                      <Input value={parent.email} onChange={(e) => updateParent(i, 'email', e.target.value)} type="email" />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Phone</Label>
                      <Input value={parent.phone} onChange={(e) => updateParent(i, 'phone', e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Relationship</Label>
                      <Select value={parent.relationship} onValueChange={(v) => updateParent(i, 'relationship', v)}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {['Father','Mother','Guardian','Uncle','Aunt','Grandparent','Other'].map((r) => (
                            <SelectItem key={r} value={r}>{r}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={addParent} className="w-full">
                <Plus className="w-4 h-4 mr-2" /> Add Another Parent
              </Button>
            </TabsContent>

            {/* Medical */}
            <TabsContent value="medical" className="space-y-4 mt-4">
              <div className="space-y-1.5">
                <Label>Medical Conditions</Label>
                <Textarea {...form.register('medicalConditions')} rows={3} placeholder="List any known medical conditions..." />
              </div>
              <div className="space-y-1.5">
                <Label>Allergies</Label>
                <Textarea {...form.register('allergies')} rows={3} placeholder="List any known allergies..." />
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create Student
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
