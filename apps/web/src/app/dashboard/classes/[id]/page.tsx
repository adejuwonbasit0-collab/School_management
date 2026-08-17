'use client';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, Users, BookOpen, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api-client';
import Link from 'next/link';

export default function ClassDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: cls, isLoading } = useQuery({ queryKey: ['class', id], queryFn: () => api.get<any>(`/v1/classes/${id}`) });

  if (isLoading || !cls) return <div className="p-6">Loading...</div>;

  return (
    <div className="space-y-6">
      <Link href="/dashboard/classes"><Button variant="ghost" size="sm"><ChevronLeft className="w-4 h-4 mr-1" />Back to Classes</Button></Link>

      <div>
        <h1 className="text-2xl font-bold">{cls.name} {cls.section}</h1>
        <p className="text-muted-foreground text-sm">{cls.enrollments?.length || 0} students enrolled • Capacity: {cls.capacity}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4"><Users className="w-4 h-4 text-blue-600 mb-1" /><p className="text-xl font-bold">{cls.enrollments?.length || 0}</p><p className="text-xs text-muted-foreground">Students</p></CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4"><BookOpen className="w-4 h-4 text-purple-600 mb-1" /><p className="text-xl font-bold">{cls.subjects?.length || 0}</p><p className="text-xs text-muted-foreground">Subjects</p></CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4"><Calendar className="w-4 h-4 text-emerald-600 mb-1" /><p className="text-xl font-bold">{cls.timetable?.length || 0}</p><p className="text-xs text-muted-foreground">Timetable Slots</p></CardContent></Card>
      </div>

      <Tabs defaultValue="students">
        <TabsList>
          <TabsTrigger value="students">Students</TabsTrigger>
          <TabsTrigger value="subjects">Subjects</TabsTrigger>
        </TabsList>
        <TabsContent value="students" className="mt-4">
          <Card className="data-table-container">
            <Table>
              <TableHeader><TableRow><TableHead>#</TableHead><TableHead>Student</TableHead><TableHead>Roll No</TableHead><TableHead>Gender</TableHead></TableRow></TableHeader>
              <TableBody>
                {cls.enrollments?.map((e: any, i: number) => (
                  <TableRow key={e.id}>
                    <TableCell className="text-sm text-muted-foreground">{i + 1}</TableCell>
                    <TableCell>
                      <Link href={`/dashboard/students/${e.student.id}`} className="flex items-center gap-2 hover:text-primary">
                        <Avatar className="w-7 h-7"><AvatarFallback className="text-xs bg-primary/10 text-primary">{e.student.user.firstName[0]}{e.student.user.lastName[0]}</AvatarFallback></Avatar>
                        <span className="text-sm font-medium">{e.student.user.firstName} {e.student.user.lastName}</span>
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{e.rollNumber || '—'}</TableCell>
                    <TableCell><Badge variant="secondary" className="text-xs">{e.student.user.gender || 'N/A'}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
        <TabsContent value="subjects" className="mt-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {cls.subjects?.map((cs: any) => (
              <Card key={cs.id} className="shadow-card"><CardContent className="pt-4 pb-4">
                <p className="font-medium text-sm">{cs.subject.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{cs.teacher ? `${cs.teacher.staff.user.firstName} ${cs.teacher.staff.user.lastName}` : 'No teacher assigned'}</p>
              </CardContent></Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
