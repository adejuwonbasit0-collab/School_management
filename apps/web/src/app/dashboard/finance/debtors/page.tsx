'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function DebtorsPage() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    apiClient.get('/analytics/finance').then(r => setReport(r.data?.data)).catch(console.error).finally(() => setLoading(false));
  }, []);

  const exportDebtors = () => window.open(`${process.env.NEXT_PUBLIC_API_URL}/analytics/export/finance`, '_blank');

  const debtors = (report?.topDebtors || []).filter((d: any) => {
    if (!search) return true;
    const name = `${d.student?.user?.firstName} ${d.student?.user?.lastName}`.toLowerCase();
    return name.includes(search.toLowerCase());
  });

  const totalOutstanding = (report?.topDebtors || []).reduce((acc: number, d: any) => {
    return acc + Number(d.totalAmount || 0) - Number(d.amountPaid || 0);
  }, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Student Debtors Report</h1>
          <p className="text-sm text-gray-500">Students with outstanding fee balances</p>
        </div>
        <Button variant="outline" onClick={exportDebtors}>⬇ Export Excel</Button>
      </div>

      {report && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Total Invoiced</p><p className="text-2xl font-bold text-blue-600">₦{Number(report.invoices?._sum?.totalAmount || 0).toLocaleString()}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Total Collected</p><p className="text-2xl font-bold text-green-600">₦{Number(report.payments?._sum?.amount || 0).toLocaleString()}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Outstanding</p><p className="text-2xl font-bold text-red-600">₦{totalOutstanding.toLocaleString()}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Pending Invoices</p><p className="text-2xl font-bold text-orange-600">{report.invoices?._count || 0}</p></Card>
        </div>
      )}

      {/* By Status */}
      {report?.byStatus && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {report.byStatus.map((s: any) => (
            <Card key={s.status} className="p-4">
              <p className="text-sm text-gray-500">{s.status}</p>
              <p className="text-xl font-bold text-gray-900">{s._count} invoices</p>
              <p className="text-sm text-gray-400">₦{Number(s._sum?.totalAmount || 0).toLocaleString()}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Debtor List */}
      <Card>
        <div className="p-4 border-b flex items-center justify-between gap-4">
          <span className="font-semibold">Top Debtors</span>
          <Input placeholder="Search student..." value={search} onChange={e => setSearch(e.target.value)} className="w-56" />
        </div>
        {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
          debtors.length === 0 ? (
            <div className="p-12 text-center text-green-600">
              <div className="text-4xl mb-3">✅</div>
              <p className="font-medium">No outstanding debtors found!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left">Student</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-right">Invoiced</th>
                    <th className="px-4 py-3 text-right">Paid</th>
                    <th className="px-4 py-3 text-right">Balance</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {debtors.map((d: any) => {
                    const balance = Number(d.totalAmount) - Number(d.amountPaid || 0);
                    return (
                      <tr key={d.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <p className="font-medium">{d.student?.user?.firstName} {d.student?.user?.lastName}</p>
                          <p className="text-xs text-gray-400">{d.student?.admissionNo}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            d.status === 'OVERDUE' ? 'bg-red-100 text-red-700' :
                            d.status === 'PARTIAL' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-orange-100 text-orange-700'
                          }`}>{d.status}</span>
                        </td>
                        <td className="px-4 py-3 text-right">₦{Number(d.totalAmount).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-green-600">₦{Number(d.amountPaid || 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-bold text-red-600">₦{balance.toLocaleString()}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => window.open(`/dashboard/finance/invoices/${d.id}`, '_blank')}
                            className="text-blue-600 hover:underline text-xs"
                          >View Invoice</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
      </Card>
    </div>
  );
}
