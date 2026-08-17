'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  ClipboardList, Check, X, Clock, AlertCircle, Save, ChevronLeft,
  ChevronRight, BarChart3, Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED';

const STATUS_CONFIG: Record<AttendanceStatus, { label: string; color: string; bg: string; icon: any }> = {
  PRESENT: { label: 'Present', color: 'text-emerald-600', bg: 'bg-emerald-100 hover:bg-emerald-200 border-emerald-300', icon: Check },
  ABSENT: { label: 'Absent', color: 'text-red-600', bg: 'bg-red-100 hover:bg-red-200 border-red-300', icon: X },
  LATE: { label: 'Late', color: 'text-amber-600', bg: 'bg-amber-100 hover:bg-amber-200 border-amber-300', icon: Clock },
  EXCUSED: { label: 'Excused', color: 'text-blue-600', bg: 'bg-blue-100 hover:bg-blue-200 border-blue-300', icon: AlertCircle },
};

export default function AttendancePage() {
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedTerm, setSelectedTerm] = useState('');
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [records, setRecords] = useState<Record<string, AttendanceStatus>>({});
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [bulkStatus, setBulkStatus] = useState<AttendanceStatus | ''>('');
  const { user } = useAuth();
  const qc = useQueryClient();

  const { data: classes } = useQuery({
    queryKey: ['classes-list'],
    queryFn: () => api.get<any>('/v1/classes'),
  });

  const { data: terms } = useQuery({
    queryKey: ['current-terms'],
    queryFn: () => api.get<any>('/v1/schools/terms?current=true'),
  });

  const { data: classStudents, isLoading: loadingStudents } = useQuery({
    queryKey: ['class-attendance', selectedClass, selectedDate],
    queryFn: () => api.get<any>(`/v1/attendance/class/${selectedClass}?date=${selectedDate}`),
    enabled: !!selectedClass,
    onSuccess: (data: any) => {
      const initial: Record<string, AttendanceStatus> = {};
      data.forEach((s: any) => {
        if (s.status) initial[s.studentId] = s.status;
      });
      setRecords(initial);
    },
  } as any);

  const { data: trendData } = useQuery({
    queryKey: ['attendance-trend', selectedClass, selectedTerm],
    queryFn: () => api.get<any>(`/v1/attendance/trend?classRoomId=${selectedClass}&termId=${selectedTerm}`),
    enabled: !!selectedClass && !!selectedTerm,
  });

  const studentsForAttendance = Array.isArray(classStudents) ? classStudents : [];

  const markMutation = useMutation({
    mutationFn: () =>
      api.post('/v1/attendance', {
        classRoomId: selectedClass,
        termId: selectedTerm,
        date: selectedDate,
        takenById: user?.id,
        records: Object.entries(records).map(([studentId, status]) => ({
          studentId,
          status,
          remarks: remarks[studentId],
        })),
      }),
    onSuccess: () => {
      toast.success('Attendance saved successfully');
      qc.invalidateQueries({ queryKey: ['class-attendance', selectedClass, selectedDate] });
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed to save attendance'),
  });

  const setStatus = (studentId: string, status: AttendanceStatus) => {
    setRecords((prev) => ({ ...prev, [studentId]: status }));
  };

  const markAll = (status: AttendanceStatus) => {
    if (!studentsForAttendance.length) return;
    const all: Record<string, AttendanceStatus> = {};
    studentsForAttendance.forEach((s: any) => { all[s.studentId] = status; });
    setRecords(all);
    setBulkStatus(status);
  };

  const moveDate = (days: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    setSelectedDate(format(d, 'yyyy-MM-dd'));
  };

  const summary = studentsForAttendance.length
    ? {
        total: studentsForAttendance.length,
        present: Object.values(records).filter((s) => s === 'PRESENT').length,
        absent: Object.values(records).filter((s) => s === 'ABSENT').length,
        late: Object.values(records).filter((s) => s === 'LATE').length,
        excused: Object.values(records).filter((s) => s === 'EXCUSED').length,
        unmarked: studentsForAttendance.length - Object.keys(records).length,
      }
    : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Attendance</h1>
          <p className="section-subtitle">Mark and track student attendance</p>
        </div>
      </div>

      <Tabs defaultValue="mark">
        <TabsList>
          <TabsTrigger value="mark"><ClipboardList className="w-4 h-4 mr-2" />Mark Attendance</TabsTrigger>
          <TabsTrigger value="reports"><BarChart3 className="w-4 h-4 mr-2" />Reports</TabsTrigger>
        </TabsList>

        {/* Mark Attendance Tab */}
        <TabsContent value="mark" className="space-y-4 mt-4">
          {/* Controls */}
          <div className="flex gap-3 flex-wrap items-center">
            <Select value={selectedClass} onValueChange={setSelectedClass}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select class" />
              </SelectTrigger>
              <SelectContent>
                {(classes?.data || classes || []).map((c: any) => (
                  <SelectItem key={c.id} value={c.id}>{c.name} {c.section || ''}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedTerm} onValueChange={setSelectedTerm}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Select term" />
              </SelectTrigger>
              <SelectContent>
                {(terms?.data || terms || []).map((t: any) => (
                  <SelectItem key={t.id} value={t.id}>{t.name} {t.isCurrent ? '(Current)' : ''}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Date picker */}
            <div className="flex items-center gap-1 border rounded-lg px-2 py-1.5">
              <Button variant="ghost" size="icon" className="w-6 h-6" onClick={() => moveDate(-1)}>
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="text-sm bg-transparent border-none outline-none"
              />
              <Button variant="ghost" size="icon" className="w-6 h-6" onClick={() => moveDate(1)}>
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>

          {selectedClass && (
            <>
              {/* Summary bar */}
              {summary && (
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { label: 'Total', value: summary.total, color: 'text-foreground' },
                    { label: 'Present', value: summary.present, color: 'text-emerald-600' },
                    { label: 'Absent', value: summary.absent, color: 'text-red-600' },
                    { label: 'Late', value: summary.late, color: 'text-amber-600' },
                    { label: 'Unmarked', value: summary.unmarked, color: 'text-muted-foreground' },
                  ].map((s) => (
                    <Card key={s.label} className="shadow-sm">
                      <CardContent className="pt-3 pb-3 text-center">
                        <p className={cn('text-2xl font-bold', s.color)}>{s.value}</p>
                        <p className="text-xs text-muted-foreground">{s.label}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {/* Bulk Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-muted-foreground">Mark all:</span>
                {(Object.keys(STATUS_CONFIG) as AttendanceStatus[]).map((status) => {
                  const cfg = STATUS_CONFIG[status];
                  const Icon = cfg.icon;
                  return (
                    <Button
                      key={status}
                      variant="outline"
                      size="sm"
                      className={cn('text-xs', cfg.color)}
                      onClick={() => markAll(status)}
                    >
                      <Icon className="w-3.5 h-3.5 mr-1" /> {cfg.label}
                    </Button>
                  );
                })}
                <Button
                  size="sm"
                  className="ml-auto"
                  onClick={() => markMutation.mutate()}
                  disabled={!selectedTerm || Object.keys(records).length === 0 || markMutation.isPending}
                >
                  {markMutation.isPending ? (
                    <span className="flex items-center gap-2"><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving...</span>
                  ) : (
                    <><Save className="w-3.5 h-3.5 mr-2" />Save Attendance</>
                  )}
                </Button>
              </div>

              {/* Student List */}
              <Card>
                <CardContent className="p-0">
                  {loadingStudents ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : studentsForAttendance.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Users className="w-10 h-10 mx-auto mb-2 opacity-20" />
                      <p>No students enrolled in this class</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {studentsForAttendance.map((s: any, idx: number) => {
                        const currentStatus = records[s.studentId];
                        return (
                          <div key={s.studentId} className="flex items-center gap-4 px-4 py-3">
                            <span className="text-sm text-muted-foreground w-6 text-center">{idx + 1}</span>
                            <Avatar className="w-8 h-8 flex-shrink-0">
                              <AvatarImage src={s.avatar} />
                              <AvatarFallback className="text-xs bg-primary/10 text-primary">
                                {s.name?.split(' ').map((n: string) => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{s.name}</p>
                              {s.rollNumber && (
                                <p className="text-xs text-muted-foreground">Roll: {s.rollNumber}</p>
                              )}
                            </div>

                            {/* Status Buttons */}
                            <div className="flex gap-1.5">
                              {(Object.keys(STATUS_CONFIG) as AttendanceStatus[]).map((status) => {
                                const cfg = STATUS_CONFIG[status];
                                const Icon = cfg.icon;
                                const isSelected = currentStatus === status;
                                return (
                                  <button
                                    key={status}
                                    type="button"
                                    onClick={() => setStatus(s.studentId, status)}
                                    title={cfg.label}
                                    className={cn(
                                      'w-8 h-8 rounded-lg border-2 flex items-center justify-center transition-all text-xs font-bold',
                                      isSelected
                                        ? `${cfg.bg} ${cfg.color} border-current scale-110 shadow-sm`
                                        : 'border-border hover:border-muted-foreground/30 text-muted-foreground hover:bg-muted',
                                    )}
                                  >
                                    <Icon className="w-3.5 h-3.5" />
                                  </button>
                                );
                              })}
                            </div>

                            {/* Quick remark */}
                            {currentStatus === 'ABSENT' || currentStatus === 'EXCUSED' ? (
                              <input
                                placeholder="Reason..."
                                className="text-xs border rounded px-2 py-1 w-28 bg-background"
                                value={remarks[s.studentId] || ''}
                                onChange={(e) => setRemarks((prev) => ({ ...prev, [s.studentId]: e.target.value }))}
                              />
                            ) : (
                              <div className="w-28" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}

          {!selectedClass && (
            <Card>
              <CardContent className="py-16 text-center">
                <ClipboardList className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground">Select a class to start marking attendance</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports" className="space-y-4 mt-4">
          <div className="flex gap-3">
            <Select value={selectedClass} onValueChange={setSelectedClass}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select class" />
              </SelectTrigger>
              <SelectContent>
                {(classes?.data || classes || []).map((c: any) => (
                  <SelectItem key={c.id} value={c.id}>{c.name} {c.section || ''}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedTerm} onValueChange={setSelectedTerm}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Select term" />
              </SelectTrigger>
              <SelectContent>
                {(terms?.data || terms || []).map((t: any) => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {trendData && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Daily Attendance Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Bar dataKey="present" fill="#10b981" name="Present" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="absent" fill="#ef4444" name="Absent" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="late" fill="#f59e0b" name="Late" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {(!selectedClass || !selectedTerm) && (
            <Card>
              <CardContent className="py-16 text-center">
                <BarChart3 className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground">Select a class and term to view attendance reports</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
