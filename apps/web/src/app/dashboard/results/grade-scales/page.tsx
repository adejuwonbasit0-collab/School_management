'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface GradeEntry { grade: string; minScore: number; maxScore: number; gradePoint: number; remark?: string }
interface GradeScale { id: string; name: string; grades: GradeEntry[] }

const DEFAULT_ENTRIES: GradeEntry[] = [
  { grade: 'A1', minScore: 75, maxScore: 100, gradePoint: 4.0, remark: 'Excellent' },
  { grade: 'B2', minScore: 70, maxScore: 74, gradePoint: 3.5, remark: 'Very Good' },
  { grade: 'B3', minScore: 65, maxScore: 69, gradePoint: 3.0, remark: 'Good' },
  { grade: 'C4', minScore: 60, maxScore: 64, gradePoint: 2.5, remark: 'Credit' },
  { grade: 'C5', minScore: 55, maxScore: 59, gradePoint: 2.0, remark: 'Credit' },
  { grade: 'C6', minScore: 50, maxScore: 54, gradePoint: 1.5, remark: 'Credit' },
  { grade: 'D7', minScore: 45, maxScore: 49, gradePoint: 1.0, remark: 'Pass' },
  { grade: 'E8', minScore: 40, maxScore: 44, gradePoint: 0.5, remark: 'Pass' },
  { grade: 'F9', minScore: 0, maxScore: 39, gradePoint: 0, remark: 'Fail' },
];

export default function GradeScalesPage() {
  const router = useRouter();
  const [scales, setScales] = useState<GradeScale[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [entries, setEntries] = useState<GradeEntry[]>(DEFAULT_ENTRIES);
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadScales(); }, []);

  const loadScales = async () => {
    try {
      const res = await apiClient.get('/results/grade-scales');
      setScales(res.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setEditId(null);
    setName('');
    setEntries(DEFAULT_ENTRIES);
    setShowForm(true);
  };

  const openEdit = (scale: GradeScale) => {
    setEditId(scale.id);
    setName(scale.name);
    setEntries(scale.grades);
    setShowForm(true);
  };

  const save = async () => {
    if (!name.trim()) return alert('Name required');
    setSaving(true);
    try {
      if (editId) {
        await apiClient.put(`/results/grade-scales/${editId}`, { name, entries });
      } else {
        await apiClient.post('/results/grade-scales', { name, entries });
      }
      setShowForm(false);
      loadScales();
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const deleteScale = async (id: string) => {
    if (!confirm('Delete this grade scale?')) return;
    try {
      await apiClient.delete(`/results/grade-scales/${id}`);
      loadScales();
    } catch (e) { alert('Delete failed'); }
  };

  const updateEntry = (i: number, field: keyof GradeEntry, value: string) => {
    setEntries(prev => prev.map((e, idx) =>
      idx === i ? { ...e, [field]: field === 'grade' || field === 'remark' ? value : parseFloat(value) || 0 } : e
    ));
  };

  const addEntry = () => setEntries(prev => [...prev, { grade: '', minScore: 0, maxScore: 100, gradePoint: 0, remark: '' }]);
  const removeEntry = (i: number) => setEntries(prev => prev.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-1 block">← Back</button>
          <h1 className="text-2xl font-bold text-gray-900">Grade Scales</h1>
          <p className="text-sm text-gray-500">Configure WAEC, NECO, or custom grading systems</p>
        </div>
        <Button onClick={openCreate}>+ New Grade Scale</Button>
      </div>

      {/* Form */}
      {showForm && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">{editId ? 'Edit' : 'Create'} Grade Scale</h2>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Scale Name</label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. WAEC A1-F9" className="max-w-xs" />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Grade</th>
                  <th className="px-3 py-2 text-left">Min %</th>
                  <th className="px-3 py-2 text-left">Max %</th>
                  <th className="px-3 py-2 text-left">Grade Point</th>
                  <th className="px-3 py-2 text-left">Remark</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, i) => (
                  <tr key={i} className="border-b">
                    <td className="px-3 py-2">
                      <Input value={entry.grade} onChange={e => updateEntry(i, 'grade', e.target.value)} className="w-16" />
                    </td>
                    <td className="px-3 py-2">
                      <Input type="number" value={entry.minScore} onChange={e => updateEntry(i, 'minScore', e.target.value)} className="w-20" />
                    </td>
                    <td className="px-3 py-2">
                      <Input type="number" value={entry.maxScore} onChange={e => updateEntry(i, 'maxScore', e.target.value)} className="w-20" />
                    </td>
                    <td className="px-3 py-2">
                      <Input type="number" step="0.1" value={entry.gradePoint} onChange={e => updateEntry(i, 'gradePoint', e.target.value)} className="w-20" />
                    </td>
                    <td className="px-3 py-2">
                      <Input value={entry.remark || ''} onChange={e => updateEntry(i, 'remark', e.target.value)} className="w-28" />
                    </td>
                    <td className="px-3 py-2">
                      <button onClick={() => removeEntry(i)} className="text-red-500 hover:text-red-700 text-xs">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex gap-3 mt-4">
            <Button variant="outline" size="sm" onClick={addEntry}>+ Add Row</Button>
            <div className="flex-1" />
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save Scale'}</Button>
          </div>
        </Card>
      )}

      {/* List */}
      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : scales.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-4xl mb-3">📊</div>
          <p className="text-gray-500">No grade scales configured</p>
          <Button className="mt-4" onClick={openCreate}>Create your first scale</Button>
        </Card>
      ) : (
        <div className="grid gap-4">
          {scales.map(scale => (
            <Card key={scale.id} className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{scale.name}</h3>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => openEdit(scale)}>Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => deleteScale(scale.id)} className="text-red-600 border-red-200 hover:bg-red-50">Delete</Button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {scale.grades.sort((a, b) => b.minScore - a.minScore).map(g => (
                  <div key={g.grade} className="text-xs bg-blue-50 border border-blue-200 rounded px-2 py-1">
                    <span className="font-bold text-blue-700">{g.grade}</span>
                    <span className="text-gray-500 ml-1">{g.minScore}–{g.maxScore}%</span>
                    <span className="text-gray-400 ml-1">({g.remark})</span>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
