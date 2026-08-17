'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function ClinicPage() {
  const [visits, setVisits] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ medicalRecordId: '', complaint: '', diagnosis: '', treatment: '', prescription: '', referral: '', followUpDate: '' });

  useEffect(() => {
    Promise.all([
      apiClient.get('/clinic/stats'),
      apiClient.get('/clinic/visits'),
    ]).then(([s, v]) => { setStats(s.data); setVisits(v.data?.data?.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  }, []);

  const saveVisit = async () => {
    if (!form.medicalRecordId || !form.complaint) return alert('Record ID and complaint required');
    setSaving(true);
    try {
      await apiClient.post('/clinic/visits', form);
      setShowForm(false);
      setForm({ medicalRecordId: '', complaint: '', diagnosis: '', treatment: '', prescription: '', referral: '', followUpDate: '' });
      const res = await apiClient.get('/clinic/visits');
      setVisits(res.data?.data?.data || []);
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clinic & Medical Records</h1>
          <p className="text-sm text-gray-500">Student and staff health management</p>
        </div>
        <Button onClick={() => setShowForm(true)}>+ Log Visit</Button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Medical Records</p><p className="text-3xl font-bold text-blue-600">{stats.totalRecords}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Visits This Month</p><p className="text-3xl font-bold text-green-600">{stats.visitsThisMonth}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Pending Follow-ups</p><p className="text-3xl font-bold text-orange-600">{stats.pendingFollowUps}</p></Card>
        </div>
      )}

      <Card>
        <div className="p-4 border-b font-semibold">Recent Clinic Visits</div>
        {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
          visits.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">🏥</div>
              <p>No clinic visits recorded</p>
              <Button className="mt-4" onClick={() => setShowForm(true)}>Log first visit</Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="px-4 py-3 text-left">Date</th><th className="px-4 py-3 text-left">Complaint</th>
                  <th className="px-4 py-3 text-left">Diagnosis</th><th className="px-4 py-3 text-left">Treatment</th>
                  <th className="px-4 py-3 text-left">Follow-up</th>
                </tr></thead>
                <tbody>{visits.map(v => (
                  <tr key={v.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">{new Date(v.visitDate).toLocaleDateString()}</td>
                    <td className="px-4 py-3 font-medium">{v.complaint}</td>
                    <td className="px-4 py-3 text-gray-500">{v.diagnosis || '—'}</td>
                    <td className="px-4 py-3 text-gray-500">{v.treatment || '—'}</td>
                    <td className="px-4 py-3">{v.followUpDate ? new Date(v.followUpDate).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
      </Card>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold mb-4">Log Clinic Visit</h2>
            <div className="space-y-3">
              <div><label className="text-sm font-medium">Medical Record ID *</label><Input placeholder="Student or staff medical record ID" value={form.medicalRecordId} onChange={e => setForm(f => ({ ...f, medicalRecordId: e.target.value }))} /></div>
              <div><label className="text-sm font-medium">Complaint *</label><textarea className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} value={form.complaint} onChange={e => setForm(f => ({ ...f, complaint: e.target.value }))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-sm font-medium">Diagnosis</label><Input value={form.diagnosis} onChange={e => setForm(f => ({ ...f, diagnosis: e.target.value }))} /></div>
                <div><label className="text-sm font-medium">Treatment</label><Input value={form.treatment} onChange={e => setForm(f => ({ ...f, treatment: e.target.value }))} /></div>
              </div>
              <div><label className="text-sm font-medium">Prescription</label><Input value={form.prescription} onChange={e => setForm(f => ({ ...f, prescription: e.target.value }))} /></div>
              <div><label className="text-sm font-medium">Follow-up Date</label><Input type="date" value={form.followUpDate} onChange={e => setForm(f => ({ ...f, followUpDate: e.target.value }))} /></div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={saveVisit} disabled={saving}>{saving ? 'Saving...' : 'Save Visit'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
