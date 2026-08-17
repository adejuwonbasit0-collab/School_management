'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api-client';
import { cn } from '@/lib/utils';

export default function GradesPage() {
  const [studentId, setStudentId] = useState('');
  const [termId, setTermId] = useState('');

  const { data: terms } = useQuery({ queryKey: ['terms'], queryFn: () => api.get<any>('/v1/schools/terms') });
  const { data: summary } = useQuery({
    queryKey: ['grade-summary', studentId, termId],
    queryFn: () => api.get<any>(`/v1/grades/student/${studentId}/summary?termId=${termId}`),
    enabled: !!studentId && !!termId,
  });

  const getGradeColor = (avg: number) => avg >= 70 ? 'text-emerald-600' : avg >= 60 ? 'text-blue-600' : avg >= 50 ? 'text-amber-600' : 'text-red-600';

  return (
    <div className="space-y-6">
      <div><h1 className="section-title">Grades & Assessment</h1><p className="section-subtitle">View and manage student grades</p></div>
      <div className="flex gap-3">
        <Select onValueChange={setTermId}>
          <SelectTrigger className="w-48"><SelectValue placeholder="Select term" /></SelectTrigger>
          <SelectContent>{(terms?.data || terms || []).map((t: any) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      {!studentId || !termId ? (
        <Card><CardContent className="py-16 text-center text-muted-foreground"><BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-20" /><p>Select a student and term to view grades</p><p className="text-xs mt-1">Navigate from a student profile to see their grades</p></CardContent></Card>
      ) : summary && (
        <Card className="data-table-container shadow-card">
          <Table>
            <TableHeader><TableRow className="bg-muted/30"><TableHead>Subject</TableHead><TableHead>Assessments</TableHead><TableHead>Average</TableHead><TableHead>Grade</TableHead></TableRow></TableHeader>
            <TableBody>
              {(summary || []).map((s: any) => (
                <TableRow key={s.subject}>
                  <TableCell className="font-medium">{s.subject}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.count} assessments</TableCell>
                  <TableCell className={cn('font-bold', getGradeColor(s.average))}>{s.average?.toFixed(1)}%</TableCell>
                  <TableCell><Badge variant="secondary" className={cn('font-bold', getGradeColor(s.average))}>{s.grade}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
