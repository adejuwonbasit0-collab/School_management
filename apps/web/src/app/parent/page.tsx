'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Child {
  id: string;
  name: string;
  relationship: string;
  admissionNo?: string;
}

interface DashboardData {
  children: Child[];
  absentLast30Days: number;
  pendingInvoices: number;
  recentResults: any[];
}

export default function ParentDashboard() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/parent-portal/dashboard')
      .then(res => setData(res.data?.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-12 text-center text-gray-400">Loading your dashboard...</div>;
  if (!data) return <div className="p-12 text-center text-red-400">Failed to load dashboard</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Parent Dashboard</h1>
        <p className="text-sm text-gray-500">Overview of your children&apos;s school activity</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5">
          <p className="text-sm text-gray-500">Children Enrolled</p>
          <p className="text-4xl font-bold text-blue-600 mt-1">{data.children.length}</p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-gray-500">Absences (Last 30 Days)</p>
          <p className={`text-4xl font-bold mt-1 ${data.absentLast30Days > 3 ? 'text-red-600' : 'text-green-600'}`}>
            {data.absentLast30Days}
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-gray-500">Pending Invoices</p>
          <p className={`text-4xl font-bold mt-1 ${data.pendingInvoices > 0 ? 'text-orange-600' : 'text-green-600'}`}>
            {data.pendingInvoices}
          </p>
        </Card>
      </div>

      {/* Children Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-3">My Children</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.children.map(child => (
            <Card key={child.id} className="p-5">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-lg">
                  {child.name.charAt(0)}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">{child.name}</p>
                  <p className="text-sm text-gray-500 capitalize">{child.relationship}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-4">
                <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=attendance`)}>
                  Attendance
                </Button>
                <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=results`)}>
                  Results
                </Button>
                <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=invoices`)}>
                  Invoices
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent Results */}
      {data.recentResults.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Recent Results</h2>
          <Card>
            <div className="divide-y">
              {data.recentResults.map(r => (
                <div key={r.id} className="px-5 py-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{r.examination?.name}</p>
                    <p className="text-sm text-gray-500">{r.student?.user?.firstName} {r.student?.user?.lastName} · {r.examination?.term?.name}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold text-blue-600">{r.grade}</span>
                    <p className="text-sm text-gray-500">{Number(r.percentage).toFixed(1)}%</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
