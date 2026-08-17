'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function StudentDashboard() {
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [attendance, setAttendance] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'results' | 'attendance' | 'fees' | 'courses'>('overview');

  useEffect(() => {
    Promise.all([
      apiClient.get('/students/my-profile').catch(() => null),
      apiClient.get('/results/students/me').catch(() => ({ data: [] })),
      apiClient.get('/attendance/my-summary').catch(() => null),
      apiClient.get('/finance/my-invoices').catch(() => ({ data: [] })),
      apiClient.get('/lms/my-courses').catch(() => ({ data: [] })),
    ]).then(([p, r, a, inv, c]) => {
      setProfile(p?.data);
      setResults(Array.isArray(r.data) ? r.data : []);
      setAttendance(a?.data);
      setInvoices(Array.isArray(inv.data) ? inv.data : inv.data?.data || []);
      setCourses(Array.isArray(c.data) ? c.data : []);
    }).finally(() => setLoading(false));
  }, []);

  const unpaidInvoices = invoices.filter(i => ['UNPAID', 'OVERDUE', 'PARTIAL'].includes(i.status));
  const attendancePct = attendance ? Math.round((attendance.present / Math.max(attendance.total, 1)) * 100) : null;
  const lastResult = results[0];

  if (loading) return <div className="p-12 text-center text-gray-400">Loading your dashboard...</div>;

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center text-3xl font-bold">
            {profile?.user?.firstName?.charAt(0) || '?'}
          </div>
          <div>
            <h1 className="text-2xl font-bold">
              Hello, {profile?.user?.firstName || 'Student'}! 👋
            </h1>
            <p className="text-blue-100">
              {profile?.enrollments?.[0]?.classRoom?.name || 'Student Portal'} · {profile?.admissionNo || ''}
            </p>
          </div>
        </div>
      </div>

      {/* Alert for unpaid fees */}
      {unpaidInvoices.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-red-500 text-xl">⚠️</span>
            <div>
              <p className="font-medium text-red-800">Outstanding Fees</p>
              <p className="text-sm text-red-600">You have {unpaidInvoices.length} unpaid invoice(s)</p>
            </div>
          </div>
          <Button onClick={() => setTab('fees')} className="bg-red-600 hover:bg-red-700">Pay Now</Button>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <div className="text-3xl mb-1">📊</div>
          <p className="text-sm text-gray-500">Last Grade</p>
          <p className="text-2xl font-bold text-blue-600">{lastResult?.grade || '—'}</p>
          {lastResult && <p className="text-xs text-gray-400">{Number(lastResult.percentage).toFixed(0)}%</p>}
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl mb-1">✅</div>
          <p className="text-sm text-gray-500">Attendance</p>
          <p className={`text-2xl font-bold ${attendancePct !== null ? (attendancePct >= 75 ? 'text-green-600' : 'text-red-600') : 'text-gray-400'}`}>
            {attendancePct !== null ? `${attendancePct}%` : '—'}
          </p>
          {attendance && <p className="text-xs text-gray-400">{attendance.present}/{attendance.total} days</p>}
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl mb-1">📚</div>
          <p className="text-sm text-gray-500">Courses</p>
          <p className="text-2xl font-bold text-purple-600">{courses.length}</p>
          <p className="text-xs text-gray-400">Enrolled</p>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl mb-1">💰</div>
          <p className="text-sm text-gray-500">Unpaid Fees</p>
          <p className={`text-2xl font-bold ${unpaidInvoices.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {unpaidInvoices.length}
          </p>
          <p className="text-xs text-gray-400">invoices</p>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit flex-wrap">
        {[
          { key: 'overview' as const, label: '🏠 Overview' },
          { key: 'results' as const, label: '📊 Results' },
          { key: 'attendance' as const, label: '✅ Attendance' },
          { key: 'fees' as const, label: '💰 Fees' },
          { key: 'courses' as const, label: '📚 Courses' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Recent results */}
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Recent Results</h2>
            {results.length === 0 ? (
              <div className="text-center text-gray-400 py-6"><p>No results published yet</p></div>
            ) : (
              <div className="space-y-3">
                {results.slice(0, 5).map(r => (
                  <div key={r.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-sm">{r.examination?.name}</p>
                      <p className="text-xs text-gray-400">{r.examination?.term?.name}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-blue-600 text-lg">{r.grade}</p>
                      <p className="text-xs text-gray-400">{Number(r.percentage).toFixed(0)}%</p>
                    </div>
                  </div>
                ))}
                <Button variant="outline" size="sm" className="w-full" onClick={() => setTab('results')}>View All Results</Button>
              </div>
            )}
          </Card>

          {/* Quick access */}
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Quick Access</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'My Results', icon: '📊', action: () => setTab('results') },
                { label: 'Attendance', icon: '✅', action: () => setTab('attendance') },
                { label: 'My Courses', icon: '📚', action: () => setTab('courses') },
                { label: 'Fee Payment', icon: '💳', action: () => setTab('fees') },
                { label: 'Documents', icon: '📁', action: () => router.push('/dashboard/documents') },
                { label: 'Messages', icon: '💬', action: () => router.push('/dashboard/communications') },
              ].map(a => (
                <button key={a.label} onClick={a.action}
                  className="flex flex-col items-center gap-2 p-4 border rounded-xl hover:bg-blue-50 hover:border-blue-300 transition-colors">
                  <span className="text-2xl">{a.icon}</span>
                  <span className="text-xs font-medium text-gray-700">{a.label}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Results tab */}
      {tab === 'results' && (
        <Card>
          {results.length === 0 ? (
            <div className="p-12 text-center text-gray-400"><div className="text-4xl mb-3">📊</div><p>No results published yet</p></div>
          ) : (
            <div className="divide-y">
              {results.map(r => (
                <div key={r.id} className="px-5 py-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{r.examination?.name}</p>
                      <p className="text-sm text-gray-500">{r.examination?.term?.name} · {r.examination?.academicYear?.name}</p>
                      {r.position && <p className="text-xs text-blue-600 mt-1">🏆 Position: {r.position}</p>}
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-blue-600">{r.grade}</p>
                      <p className="text-sm text-gray-500">{Number(r.percentage).toFixed(1)}%</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Attendance tab */}
      {tab === 'attendance' && attendance && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Days', value: attendance.total, color: 'text-gray-900' },
              { label: 'Present', value: attendance.present, color: 'text-green-600' },
              { label: 'Absent', value: attendance.absent, color: 'text-red-600' },
              { label: 'Late', value: attendance.late || 0, color: 'text-yellow-600' },
            ].map(s => (
              <Card key={s.label} className="p-4 text-center">
                <p className="text-sm text-gray-500">{s.label}</p>
                <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
              </Card>
            ))}
          </div>
          <Card className="p-5">
            <h2 className="font-semibold mb-3">Attendance Rate</h2>
            <div className="w-full bg-gray-100 rounded-full h-4 mb-2">
              <div className={`h-4 rounded-full transition-all ${attendancePct! >= 75 ? 'bg-green-500' : 'bg-red-500'}`}
                style={{ width: `${attendancePct}%` }} />
            </div>
            <p className={`text-sm font-medium ${attendancePct! >= 75 ? 'text-green-600' : 'text-red-600'}`}>
              {attendancePct}% {attendancePct! >= 75 ? '✓ Good standing' : '⚠ Below minimum (75%)'}
            </p>
          </Card>
        </div>
      )}

      {/* Fees tab */}
      {tab === 'fees' && (
        <div className="space-y-4">
          {invoices.length === 0 ? (
            <Card className="p-12 text-center text-gray-400"><div className="text-4xl mb-3">💰</div><p>No invoices found</p></Card>
          ) : invoices.map(inv => {
            const balance = Number(inv.totalAmount) - Number(inv.amountPaid || 0);
            return (
              <Card key={inv.id} className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold">{inv.feeStructure?.name || 'Invoice'}</p>
                    <p className="text-sm text-gray-500">{inv.term?.name}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    inv.status === 'PAID' ? 'bg-green-100 text-green-700' :
                    inv.status === 'OVERDUE' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>{inv.status}</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Total:</span><span className="font-medium">₦{Number(inv.totalAmount).toLocaleString()}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Paid:</span><span className="text-green-600">₦{Number(inv.amountPaid || 0).toLocaleString()}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Balance:</span><span className="font-bold text-red-600">₦{balance.toLocaleString()}</span></div>
                </div>
                {inv.status !== 'PAID' && (
                  <Button className="mt-3 w-full" onClick={() => router.push(`/dashboard/finance?pay=${inv.id}`)}>
                    💳 Pay ₦{balance.toLocaleString()}
                  </Button>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Courses tab */}
      {tab === 'courses' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.length === 0 ? (
            <Card className="col-span-3 p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">📚</div>
              <p>Not enrolled in any courses yet</p>
            </Card>
          ) : courses.map(course => {
            const meta = course.content || {};
            return (
              <Card key={course.id} className="p-5 hover:shadow-md transition-shadow">
                <div className="w-full h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg mb-4 flex items-center justify-center text-white text-3xl">📚</div>
                <h3 className="font-semibold">{course.title}</h3>
                {meta.description && <p className="text-sm text-gray-500 mt-1 line-clamp-2">{meta.description}</p>}
                <div className="flex justify-between items-center mt-3">
                  <span className="text-xs text-gray-400">{(meta.modules || []).length} materials</span>
                  <Button size="sm" onClick={() => router.push('/dashboard/lms')}>Open →</Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
