'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function ParentChildrenPage() {
  const router = useRouter();
  const [children, setChildren] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/parent-portal/children')
      .then(res => setChildren(res.data?.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-12 text-center text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">My Children</h1>
      {children.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-4xl mb-3">👨‍👩‍👧‍👦</div>
          <p className="text-gray-500">No children linked to your account</p>
          <p className="text-sm text-gray-400 mt-1">Contact the school admin to link your children</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {children.map(child => {
            const enrollment = child.enrollments?.[0];
            return (
              <Card key={child.id} className="p-5">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-xl font-bold">
                    {child.user?.firstName?.charAt(0)}
                  </div>
                  <div>
                    <p className="text-lg font-bold text-gray-900">{child.user?.firstName} {child.user?.lastName}</p>
                    <p className="text-sm text-gray-500">{child.admissionNo}</p>
                    {enrollment && (
                      <p className="text-sm text-blue-600">{enrollment.classRoom?.name} · {enrollment.academicYear?.name}</p>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=attendance`)}>
                    📅 Attendance
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=results`)}>
                    📊 Results
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => router.push(`/parent/children/${child.id}?tab=invoices`)}>
                    💰 Fees
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
