'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function ScholarshipsPage() {
  const [scholarships, setScholarships] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', type: 'PERCENTAGE', value: 0, isActive: true });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiClient.get('/finance/scholarships').then(r => setScholarships(r.data?.data || r.data || [])).catch(console.error).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await apiClient.post('/finance/scholarships', form);
      setShowForm(false);
      setForm({ name: '', description: '', type: 'PERCENTAGE', value: 0, isActive: true });
      const r = await apiClient.get('/finance/scholarships');
      setScholarships(r.data?.data || r.data || []);
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const toggle = async (id: string, isActive: boolean) => {
    await apiClient.put(`/finance/scholarships/${id}`, { isActive: !isActive });
    setScholarships(prev => prev.map(s => s.id === id ? { ...s, isActive: !isActive } : s));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scholarships & Discounts</h1>
          <p className="text-sm text-gray-500">Manage fee waivers, scholarships, and discount schemes</p>
        </div>
        <Button onClick={() => setShowForm(true)}>+ New Scholarship</Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4"><p className="text-sm text-gray-500">Total Schemes</p><p className="text-3xl font-bold text-blue-600">{scholarships.length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Active</p><p className="text-3xl font-bold text-green-600">{scholarships.filter(s => s.isActive).length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Percentage-Based</p><p className="text-3xl font-bold text-purple-600">{scholarships.filter(s => s.type === 'PERCENTAGE').length}</p></Card>
      </div>

      <Card>
        {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
          scholarships.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">🎓</div>
              <p>No scholarships configured</p>
              <Button className="mt-4" onClick={() => setShowForm(true)}>Create first scholarship</Button>
            </div>
          ) : (
            <div className="divide-y">
              {scholarships.map(s => (
                <div key={s.id} className="px-5 py-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold">{s.name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${s.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    {s.description && <p className="text-sm text-gray-500 mt-0.5">{s.description}</p>}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-2xl font-bold text-blue-600">
                        {s.type === 'PERCENTAGE' ? `${Number(s.value)}%` : `₦${Number(s.value).toLocaleString()}`}
                      </p>
                      <p className="text-xs text-gray-400">{s.type === 'PERCENTAGE' ? 'discount' : 'fixed waiver'}</p>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => toggle(s.id, s.isActive)}>
                      {s.isActive ? 'Disable' : 'Enable'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
      </Card>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">New Scholarship / Discount</h2>
            <div className="space-y-3">
              <Input placeholder="Name (e.g. Academic Excellence Award)" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">Type</label>
                  <select className="w-full border rounded-lg px-3 py-2 text-sm mt-1" value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                    <option value="PERCENTAGE">Percentage (%)</option>
                    <option value="FIXED">Fixed Amount (₦)</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">{form.type === 'PERCENTAGE' ? 'Percentage' : 'Amount (₦)'}</label>
                  <Input type="number" value={form.value} onChange={e => setForm(f => ({ ...f, value: +e.target.value }))} className="mt-1" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
