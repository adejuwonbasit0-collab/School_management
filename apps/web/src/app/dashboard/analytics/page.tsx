'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const COLORS = ['#1a56db','#7c3aed','#059669','#d97706','#dc2626','#0891b2'];

function StatCard({ label, value, sub, color = 'text-blue-600' }: any) {
  return (
    <Card className="p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </Card>
  );
}

function SimpleBar({ data, valueKey, labelKey, color = '#1a56db' }: any) {
  if (!data?.length) return <div className="text-center text-gray-400 py-8">No data</div>;
  const max = Math.max(...data.map((d: any) => d[valueKey]));
  return (
    <div className="space-y-2">
      {data.map((d: any, i: number) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          <span className="w-24 text-gray-600 truncate">{d[labelKey]}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div className="h-5 rounded-full flex items-center px-2 text-white text-xs font-medium"
              style={{ width: `${max > 0 ? (d[valueKey] / max) * 100 : 0}%`, backgroundColor: color, minWidth: d[valueKey] > 0 ? '2rem' : 0 }}>
              {d[valueKey] > 0 ? d[valueKey].toLocaleString() : ''}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [revenue, setRevenue] = useState<any[]>([]);
  const [students, setStudents] = useState<any>(null);
  const [academic, setAcademic] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    Promise.all([
      apiClient.get('/analytics/dashboard'),
      apiClient.get('/analytics/revenue'),
      apiClient.get('/analytics/students'),
      apiClient.get('/analytics/academic'),
    ]).then(([d, r, s, a]) => {
      setDashboard(d.data?.data);
      setRevenue(r.data?.data || []);
      setStudents(s.data?.data);
      setAcademic(a.data?.data || []);
    }).catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const exportReport = (type: string) => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/analytics/export/${type}`, '_blank');
  };

  const tabs = ['overview', 'finance', 'students', 'academic'];

  if (loading) return <div className="p-12 text-center text-gray-400">Loading analytics...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics & Reports</h1>
          <p className="text-sm text-gray-500">Business intelligence and performance insights</p>
        </div>
        <div className="flex gap-2">
          {['finance', 'students', 'attendance'].map(t => (
            <Button key={t} size="sm" variant="outline" onClick={() => exportReport(t)}>
              ⬇ {t.charAt(0).toUpperCase() + t.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all capitalize ${activeTab === t ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && dashboard && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Students" value={dashboard.students?.total} sub={`+${dashboard.students?.newThisMonth} this month`} color="text-blue-600" />
            <StatCard label="Active Staff" value={dashboard.staff?.active} sub={`of ${dashboard.staff?.total} total`} color="text-green-600" />
            <StatCard label="Revenue This Month" value={`₦${Number(dashboard.finance?.revenueThisMonth || 0).toLocaleString()}`} sub={`${dashboard.finance?.revenueGrowth}% vs last month`} color="text-purple-600" />
            <StatCard label="Unpaid Invoices" value={dashboard.finance?.unpaidInvoices} sub="Require follow-up" color="text-red-600" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Classes" value={dashboard.academic?.totalClasses} color="text-indigo-600" />
            <StatCard label="Present Today" value={dashboard.attendance?.presentToday} color="text-teal-600" />
            <StatCard label="Pending Admissions" value={dashboard.admissions?.pending} color="text-orange-600" />
            <StatCard label="Revenue Growth" value={`${dashboard.finance?.revenueGrowth}%`} color={Number(dashboard.finance?.revenueGrowth) >= 0 ? 'text-green-600' : 'text-red-600'} />
          </div>
        </div>
      )}

      {/* Finance Tab */}
      {activeTab === 'finance' && (
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Monthly Revenue (This Year)</h2>
            <SimpleBar data={revenue} valueKey="collected" labelKey="month" color="#1a56db" />
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="p-5">
              <h2 className="font-semibold mb-4">Invoiced vs Collected</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="pb-2 text-left">Month</th><th className="pb-2 text-right">Invoiced</th><th className="pb-2 text-right">Collected</th></tr></thead>
                  <tbody>
                    {revenue.map((r, i) => (
                      <tr key={i} className="border-b">
                        <td className="py-2">{r.month}</td>
                        <td className="py-2 text-right">₦{Number(r.invoiced).toLocaleString()}</td>
                        <td className="py-2 text-right text-green-600">₦{Number(r.collected).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card className="p-5">
              <h2 className="font-semibold mb-4">Collection Rate</h2>
              <div className="space-y-3">
                {revenue.map((r, i) => {
                  const rate = r.invoiced > 0 ? (r.collected / r.invoiced) * 100 : 0;
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span>{r.month}</span><span className="font-medium">{rate.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="h-2 rounded-full" style={{ width: `${Math.min(rate, 100)}%`, backgroundColor: rate >= 80 ? '#059669' : rate >= 50 ? '#d97706' : '#dc2626' }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Students Tab */}
      {activeTab === 'students' && students && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Students by Gender</h2>
            <div className="flex gap-4">
              {(students.byGender || []).map((g: any, i: number) => (
                <div key={g.gender} className="flex-1 text-center p-4 rounded-lg" style={{ backgroundColor: COLORS[i] + '20' }}>
                  <p className="text-3xl font-bold" style={{ color: COLORS[i] }}>{g._count}</p>
                  <p className="text-sm text-gray-600 capitalize">{g.gender || 'Unknown'}</p>
                </div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h2 className="font-semibold mb-4">Student Status</h2>
            <div className="space-y-2">
              {(students.statusBreakdown || []).map((s: any, i: number) => (
                <div key={s.status} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{s.status}</span>
                  <span className="font-semibold" style={{ color: COLORS[i] }}>{s._count}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card className="p-5 md:col-span-2">
            <h2 className="font-semibold mb-4">Enrollment Trend (Last 6 Months)</h2>
            <SimpleBar data={students.enrollmentTrend || []} valueKey="count" labelKey="month" color="#7c3aed" />
          </Card>
        </div>
      )}

      {/* Academic Tab */}
      {activeTab === 'academic' && (
        <Card>
          <div className="p-4 border-b font-semibold">Examination Performance History</div>
          {academic.length === 0 ? (
            <div className="p-12 text-center text-gray-400">No published examination results yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left">Examination</th>
                    <th className="px-4 py-3 text-left">Term</th>
                    <th className="px-4 py-3 text-right">Students</th>
                    <th className="px-4 py-3 text-right">Average Score</th>
                    <th className="px-4 py-3 text-right">Pass Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {academic.map((e: any) => (
                    <tr key={e.examId} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{e.examName}</td>
                      <td className="px-4 py-3 text-gray-500">{e.term || '—'}</td>
                      <td className="px-4 py-3 text-right">{e.studentCount}</td>
                      <td className="px-4 py-3 text-right font-medium">{e.averageScore}%</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-medium ${Number(e.passRate) >= 70 ? 'text-green-600' : Number(e.passRate) >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {e.passRate}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
