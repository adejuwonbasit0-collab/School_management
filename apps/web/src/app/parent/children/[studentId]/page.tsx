'use client';

import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

type Tab = 'attendance' | 'results' | 'invoices';

const STATUS_COLORS: Record<string, string> = {
  PRESENT: 'bg-green-100 text-green-700',
  ABSENT: 'bg-red-100 text-red-700',
  LATE: 'bg-yellow-100 text-yellow-700',
  EXCUSED: 'bg-blue-100 text-blue-700',
  UNPAID: 'bg-red-100 text-red-700',
  PARTIAL: 'bg-yellow-100 text-yellow-700',
  PAID: 'bg-green-100 text-green-700',
  OVERDUE: 'bg-red-100 text-red-800',
};

export default function ChildDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>((searchParams.get('tab') as Tab) || 'attendance');
  const [attendance, setAttendance] = useState<{ records: any[]; summary: any } | null>(null);
  const [results, setResults] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTab(tab);
  }, [tab, studentId]);

  const loadTab = async (t: Tab) => {
    setLoading(true);
    try {
      if (t === 'attendance') {
        const res = await apiClient.get(`/parent-portal/children/${studentId}/attendance`);
        setAttendance(res.data?.data);
      } else if (t === 'results') {
        const res = await apiClient.get(`/parent-portal/children/${studentId}/results`);
        setResults(res.data?.data || []);
      } else if (t === 'invoices') {
        const res = await apiClient.get(`/parent-portal/children/${studentId}/invoices`);
        setInvoices(res.data?.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'attendance', label: '📅 Attendance' },
    { key: 'results', label: '📊 Results' },
    { key: 'invoices', label: '💰 Invoices' },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="text-blue-600 hover:underline text-sm">← Back</button>
        <h1 className="text-2xl font-bold text-gray-900">Child Overview</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-400">Loading...</div>
      ) : (
        <>
          {/* Attendance Tab */}
          {tab === 'attendance' && attendance && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Total Days', value: attendance.summary.total, color: 'text-gray-900' },
                  { label: 'Present', value: attendance.summary.present, color: 'text-green-600' },
                  { label: 'Absent', value: attendance.summary.absent, color: 'text-red-600' },
                  { label: 'Late', value: attendance.summary.late, color: 'text-yellow-600' },
                ].map(s => (
                  <Card key={s.label} className="p-4 text-center">
                    <p className="text-sm text-gray-500">{s.label}</p>
                    <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                  </Card>
                ))}
              </div>

              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left">Date</th>
                        <th className="px-4 py-3 text-left">Class</th>
                        <th className="px-4 py-3 text-left">Status</th>
                        <th className="px-4 py-3 text-left">Remarks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attendance.records.map(r => (
                        <tr key={r.id} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-3">{new Date(r.date).toLocaleDateString()}</td>
                          <td className="px-4 py-3 text-gray-600">{r.classRoom?.name || '—'}</td>
                          <td className="px-4 py-3">
                            <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[r.status] || 'bg-gray-100'}`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500">{r.remarks || '—'}</td>
                        </tr>
                      ))}
                      {attendance.records.length === 0 && (
                        <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No attendance records</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* Results Tab */}
          {tab === 'results' && (
            <Card>
              {results.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">📊</div>
                  <p>No published results yet</p>
                </div>
              ) : (
                <div className="divide-y">
                  {results.map(r => (
                    <div key={r.id} className="px-5 py-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-semibold text-gray-900">{r.examination?.name}</p>
                          <p className="text-sm text-gray-500">
                            {r.examination?.term?.name} · {r.examination?.academicYear?.name}
                          </p>
                          {r.position && (
                            <p className="text-xs text-blue-600 mt-1">Position: {r.position}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-blue-600">{r.grade}</div>
                          <div className="text-sm text-gray-500">{Number(r.percentage).toFixed(1)}%</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Invoices Tab */}
          {tab === 'invoices' && (
            <div className="space-y-4">
              {invoices.length === 0 ? (
                <Card className="p-12 text-center">
                  <div className="text-4xl mb-3">💰</div>
                  <p className="text-gray-400">No invoices found</p>
                </Card>
              ) : (
                invoices.map(inv => (
                  <Card key={inv.id} className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <p className="font-semibold text-gray-900">{inv.feeStructure?.name || 'Invoice'}</p>
                        <p className="text-sm text-gray-500">{inv.term?.name}</p>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[inv.status] || 'bg-gray-100'}`}>
                          {inv.status}
                        </span>
                        <p className="text-lg font-bold text-gray-900 mt-1">
                          ₦{Number(inv.totalAmount).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500 space-y-1">
                      <div className="flex justify-between">
                        <span>Amount Paid:</span>
                        <span className="text-green-600 font-medium">₦{Number(inv.amountPaid || 0).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Balance:</span>
                        <span className="text-red-600 font-medium">₦{Number(inv.balance || inv.totalAmount - (inv.amountPaid || 0)).toLocaleString()}</span>
                      </div>
                    </div>
                    {inv.status !== 'PAID' && (
                      <Button className="mt-4 w-full" size="sm">Pay Now</Button>
                    )}
                  </Card>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
