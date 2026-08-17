'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function TeacherDashboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [timetable, setTimetable] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'timetable' | 'attendance' | 'results'>('overview');

  useEffect(() => {
    Promise.all([
      apiClient.get('/teachers/my-profile').catch(() => null),
      apiClient.get('/timetable/teacher/me').catch(() => ({ data: [] })),
      apiClient.get('/classes?myClasses=true').catch(() => ({ data: [] })),
    ]).then(([profile, tt, cls]) => {
      setData(profile?.data?.data);
      setTimetable(tt.data?.data || []);
      setClasses(Array.isArray(cls.data?.data) ? cls.data.data : cls.data?.data?.data || []);
    }).finally(() => setLoading(false));
  }, []);

  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

  const todaySlots = timetable.filter(slot => {
    const dayMap: Record<number, number> = { 1: 1, 2: 2, 3: 3, 4: 4, 5: 5 };
    const todayNum = new Date().getDay();
    return slot.dayOfWeek === todayNum;
  });

  if (loading) return <div className="p-12 text-center text-gray-400">Loading teacher dashboard...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Teacher Portal</h1>
          <p className="text-sm text-gray-500">
            {data?.user ? `Welcome back, ${data.user.firstName} ${data.user.lastName}` : 'Your teaching workspace'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/dashboard/results')}>📊 Enter Scores</Button>
          <Button onClick={() => router.push('/dashboard/lms')}>📚 My Courses</Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Today's Classes", value: todaySlots.length, color: 'text-blue-600', icon: '🏫' },
          { label: 'My Classes', value: classes.length, color: 'text-green-600', icon: '👩‍🏫' },
          { label: 'Subjects', value: timetable.reduce((acc: Set<string>, s: any) => { acc.add(s.subject?.id); return acc; }, new Set()).size, color: 'text-purple-600', icon: '📖' },
          { label: 'Students', value: classes.reduce((acc, c) => acc + (c._count?.enrollments || 0), 0), color: 'text-orange-600', icon: '👥' },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{s.icon}</span>
              <div>
                <p className="text-sm text-gray-500">{s.label}</p>
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'overview' as const, label: '📊 Overview' },
          { key: 'timetable' as const, label: '📅 Timetable' },
          { key: 'attendance' as const, label: '✅ Attendance' },
          { key: 'results' as const, label: '📝 Results' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Today's schedule */}
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Today&apos;s Schedule</h2>
            {todaySlots.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                <div className="text-3xl mb-2">🎉</div>
                <p>No classes today</p>
              </div>
            ) : (
              <div className="space-y-2">
                {todaySlots.sort((a, b) => a.startTime.localeCompare(b.startTime)).map((slot: any) => (
                  <div key={slot.id} className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                    <div className="text-center min-w-[60px]">
                      <p className="text-xs font-bold text-blue-600">{slot.startTime}</p>
                      <p className="text-xs text-gray-400">{slot.endTime}</p>
                    </div>
                    <div>
                      <p className="font-medium text-sm">{slot.subject?.name}</p>
                      <p className="text-xs text-gray-500">{slot.classRoom?.name} {slot.room ? `· ${slot.room}` : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* My Classes */}
          <Card className="p-5">
            <h2 className="font-semibold mb-4">My Classes</h2>
            {classes.length === 0 ? (
              <div className="text-center text-gray-400 py-8">No classes assigned</div>
            ) : (
              <div className="space-y-2">
                {classes.map((cls: any) => (
                  <div key={cls.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                    <div>
                      <p className="font-medium text-sm">{cls.name}{cls.section ? ` ${cls.section}` : ''}</p>
                      <p className="text-xs text-gray-400">{cls._count?.enrollments || 0} students</p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => router.push(`/dashboard/attendance?classRoomId=${cls.id}`)}>Attendance</Button>
                      <Button size="sm" variant="outline" onClick={() => router.push(`/dashboard/results?classRoomId=${cls.id}`)}>Results</Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Quick actions */}
          <Card className="p-5 md:col-span-2">
            <h2 className="font-semibold mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Mark Attendance', icon: '✅', href: '/dashboard/attendance' },
                { label: 'Enter Results', icon: '📝', href: '/dashboard/results' },
                { label: 'View Timetable', icon: '📅', href: '/dashboard/timetable' },
                { label: 'Create Course', icon: '📚', href: '/dashboard/lms' },
                { label: 'Send Message', icon: '💬', href: '/dashboard/communications' },
                { label: 'Upload Document', icon: '📁', href: '/dashboard/documents' },
                { label: 'View Students', icon: '👥', href: '/dashboard/students' },
                { label: 'Examinations', icon: '📋', href: '/dashboard/examinations' },
              ].map(action => (
                <button key={action.label} onClick={() => router.push(action.href)}
                  className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-blue-50 hover:border-blue-300 transition-colors">
                  <span className="text-2xl">{action.icon}</span>
                  <span className="text-xs font-medium text-gray-700 text-center">{action.label}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Timetable view */}
      {tab === 'timetable' && (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-gray-600">Time</th>
                {DAYS.map(d => <th key={d} className="px-4 py-3 text-center text-gray-600">{d}</th>)}
              </tr>
            </thead>
            <tbody>
              {['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'].map(time => (
                <tr key={time} className="border-t">
                  <td className="px-4 py-3 text-gray-500 text-xs">{time}</td>
                  {DAYS.map((_, di) => {
                    const slot = timetable.find(s => s.dayOfWeek === di + 1 && s.startTime === time);
                    return (
                      <td key={di} className="px-2 py-2">
                        {slot ? (
                          <div className="bg-blue-100 text-blue-800 rounded p-2 text-xs">
                            <p className="font-medium">{slot.subject?.name}</p>
                            <p className="text-blue-600">{slot.classRoom?.name}</p>
                          </div>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Attendance quick mark */}
      {tab === 'attendance' && (
        <Card className="p-5">
          <h2 className="font-semibold mb-4">Mark Attendance</h2>
          <p className="text-sm text-gray-500 mb-4">Select a class to mark today&apos;s attendance:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {classes.map((cls: any) => (
              <button key={cls.id} onClick={() => router.push(`/dashboard/attendance?classRoomId=${cls.id}`)}
                className="flex items-center justify-between p-4 border rounded-xl hover:bg-green-50 hover:border-green-300 transition-colors text-left">
                <div>
                  <p className="font-medium">{cls.name}{cls.section ? ` ${cls.section}` : ''}</p>
                  <p className="text-sm text-gray-400">{cls._count?.enrollments || 0} students</p>
                </div>
                <span className="text-green-600 text-2xl">✅</span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Results quick access */}
      {tab === 'results' && (
        <Card className="p-5">
          <h2 className="font-semibold mb-4">Enter Results</h2>
          <p className="text-sm text-gray-500 mb-4">Go to the Results module to enter scores for your classes:</p>
          <Button onClick={() => router.push('/dashboard/results')} className="w-full md:w-auto">
            📝 Open Results Module
          </Button>
        </Card>
      )}
    </div>
  );
}
