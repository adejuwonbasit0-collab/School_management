'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  User, Phone, Mail, MapPin, Calendar, BookOpen, DollarSign,
  ClipboardList, FileText, ChevronLeft, Edit, Printer,
  Heart, School, Users, CheckCircle, XCircle, Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import Link from 'next/link';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

export default function StudentProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();

  const { data: student, isLoading } = useQuery({
    queryKey: ['student', id],
    queryFn: () => api.get<any>(`/v1/students/${id}`),
  });

  if (isLoading) return <StudentProfileSkeleton />;
  if (!student) return <div>Student not found</div>;

  const enrollment = student.enrollments?.[0];
  const primaryParent = student.parents?.find((p: any) => p.isPrimary) || student.parents?.[0];
  const totalFees = student.feeInvoices?.reduce((sum: number, inv: any) => sum + Number(inv.totalAmount), 0) || 0;
  const paidFees = student.feeInvoices?.reduce((sum: number, inv: any) => sum + Number(inv.paidAmount), 0) || 0;

  return (
    <div className="space-y-6">
      {/* Back & Actions */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard/students">
          <Button variant="ghost" size="sm">
            <ChevronLeft className="w-4 h-4 mr-1" /> Back to Students
          </Button>
        </Link>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Printer className="w-4 h-4 mr-2" /> Print Profile
          </Button>
          {hasPermission('students:students:UPDATE') && (
            <Link href={`/dashboard/students/${id}/edit`}>
              <Button size="sm">
                <Edit className="w-4 h-4 mr-2" /> Edit
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Profile Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-6">
            <Avatar className="w-20 h-20">
              <AvatarImage src={student.user.avatar} />
              <AvatarFallback className="text-xl bg-primary/10 text-primary font-bold">
                {student.user.firstName[0]}{student.user.lastName[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-2xl font-bold">
                    {student.user.firstName} {student.user.middleName || ''} {student.user.lastName}
                  </h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <Badge variant="outline" className="font-mono">{student.admissionNo}</Badge>
                    {enrollment && (
                      <Badge variant="secondary">
                        <School className="w-3 h-3 mr-1" />
                        {enrollment.classRoom?.name} {enrollment.classRoom?.section || ''}
                      </Badge>
                    )}
                    <Badge className={student.user.status === 'ACTIVE' ? 'badge-success' : 'badge-danger'}>
                      {student.user.status}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                {[
                  { icon: Mail, label: student.user.email },
                  { icon: Phone, label: student.user.phone || 'No phone' },
                  { icon: Calendar, label: student.user.dateOfBirth ? format(new Date(student.user.dateOfBirth), 'dd MMM yyyy') : 'DOB not set' },
                  { icon: Heart, label: student.bloodGroup?.replace('_', ' ') || 'Blood group N/A' },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Fees', value: `₦${totalFees.toLocaleString()}`, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
          { label: 'Fees Paid', value: `₦${paidFees.toLocaleString()}`, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
          { label: 'Outstanding', value: `₦${(totalFees - paidFees).toLocaleString()}`, color: totalFees - paidFees > 0 ? 'text-red-600' : 'text-emerald-600', bg: 'bg-red-50 dark:bg-red-950/30' },
          { label: 'Borrowed Books', value: student.libraryBorrows?.length || 0, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-4 pb-4">
              <p className={cn('text-xl font-bold', s.color)}>{s.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="attendance">Attendance</TabsTrigger>
          <TabsTrigger value="fees">Fees</TabsTrigger>
          <TabsTrigger value="parents">Parents</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4 mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Personal Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {[
                  ['Full Name', `${student.user.firstName} ${student.user.lastName}`],
                  ['Gender', student.user.gender || '—'],
                  ['Date of Birth', student.user.dateOfBirth ? format(new Date(student.user.dateOfBirth), 'dd MMMM yyyy') : '—'],
                  ['Nationality', student.nationality || '—'],
                  ['Religion', student.religion || '—'],
                  ['Mother Tongue', student.motherTongue || '—'],
                  ['Address', student.user.address || '—'],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between py-1 border-b last:border-0">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-medium text-right max-w-[60%]">{val}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Academic Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {[
                  ['Admission No', student.admissionNo],
                  ['Admission Date', format(new Date(student.admissionDate), 'dd MMM yyyy')],
                  ['Current Class', enrollment ? `${enrollment.classRoom?.name} ${enrollment.classRoom?.section || ''}` : 'Not enrolled'],
                  ['Academic Year', enrollment?.academicYear?.name || '—'],
                  ['Roll Number', enrollment?.rollNumber || '—'],
                  ['Previous School', student.previousSchool || '—'],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between py-1 border-b last:border-0">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-medium">{val}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Recent Attendance */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Recent Attendance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-1.5 flex-wrap">
                {student.attendance?.slice(0, 30).map((a: any) => (
                  <div
                    key={a.id}
                    title={`${format(new Date(a.date), 'dd MMM')}: ${a.status}`}
                    className={cn(
                      'w-6 h-6 rounded text-xs flex items-center justify-center font-bold cursor-default',
                      a.status === 'PRESENT' ? 'bg-emerald-100 text-emerald-700' :
                      a.status === 'ABSENT' ? 'bg-red-100 text-red-700' :
                      a.status === 'LATE' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-600',
                    )}
                  >
                    {a.status[0]}
                  </div>
                ))}
                {student.attendance?.length === 0 && (
                  <p className="text-muted-foreground text-sm">No attendance records</p>
                )}
              </div>
              <div className="flex gap-4 mt-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm" />Present</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-red-500 rounded-sm" />Absent</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-amber-500 rounded-sm" />Late</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Fees Tab */}
        <TabsContent value="fees" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Fee Invoices</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invoice No</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Paid</TableHead>
                    <TableHead>Balance</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Due Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {student.feeInvoices?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">No invoices</TableCell>
                    </TableRow>
                  )}
                  {student.feeInvoices?.map((inv: any) => (
                    <TableRow key={inv.id}>
                      <TableCell><Link href={`/dashboard/finance/invoices/${inv.id}`} className="text-primary hover:underline font-mono text-sm">{inv.invoiceNo}</Link></TableCell>
                      <TableCell>₦{Number(inv.totalAmount).toLocaleString()}</TableCell>
                      <TableCell className="text-emerald-600">₦{Number(inv.paidAmount).toLocaleString()}</TableCell>
                      <TableCell className={Number(inv.totalAmount) - Number(inv.paidAmount) > 0 ? 'text-red-600' : 'text-emerald-600'}>
                        ₦{(Number(inv.totalAmount) - Number(inv.paidAmount)).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={
                          inv.status === 'PAID' ? 'badge-success' :
                          inv.status === 'PARTIAL' ? 'badge-warning' :
                          inv.status === 'OVERDUE' ? 'badge-danger' : 'badge-neutral'
                        }>
                          {inv.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {inv.dueDate ? format(new Date(inv.dueDate), 'dd MMM yyyy') : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Parents Tab */}
        <TabsContent value="parents" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {student.parents?.map((sp: any) => (
              <Card key={sp.id}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3 mb-3">
                    <Avatar className="w-10 h-10">
                      <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                        {sp.parent?.user?.firstName?.[0]}{sp.parent?.user?.lastName?.[0]}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-semibold">{sp.parent?.user?.firstName} {sp.parent?.user?.lastName}</p>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">{sp.relationship}</Badge>
                        {sp.isPrimary && <Badge className="text-xs badge-info">Primary</Badge>}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="w-3.5 h-3.5" /> {sp.parent?.user?.email}
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Phone className="w-3.5 h-3.5" /> {sp.parent?.user?.phone || 'No phone'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader className="pb-2 flex-row items-center justify-between">
              <CardTitle className="text-sm font-semibold">Documents</CardTitle>
              <Button size="sm" variant="outline"><FileText className="w-4 h-4 mr-2" /> Upload</Button>
            </CardHeader>
            <CardContent>
              {student.documents?.length === 0 ? (
                <p className="text-center text-muted-foreground py-8 text-sm">No documents uploaded</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {student.documents?.map((doc: any) => (
                    <a key={doc.id} href={doc.url} target="_blank" rel="noreferrer"
                      className="flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                      <FileText className="w-8 h-8 text-primary" />
                      <div>
                        <p className="text-sm font-medium line-clamp-1">{doc.name}</p>
                        <p className="text-xs text-muted-foreground">{doc.type}</p>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StudentProfileSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-32" />
      <Card><CardContent className="pt-6"><div className="flex gap-6"><Skeleton className="w-20 h-20 rounded-full" /><div className="flex-1 space-y-2"><Skeleton className="h-7 w-48" /><Skeleton className="h-5 w-80" /></div></div></CardContent></Card>
      <div className="grid grid-cols-4 gap-4">{Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
    </div>
  );
}
