'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'academic-years' | 'terms' | 'departments' | 'notifications' | 'payments' | 'school-info';

const VALID_TABS: Tab[] = ['academic-years', 'terms', 'departments', 'notifications', 'payments', 'school-info'];

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const initialTab = VALID_TABS.includes(searchParams.get('tab') as Tab)
    ? (searchParams.get('tab') as Tab)
    : 'academic-years';
  const [tab, setTab] = useState<Tab>(initialTab);
  const [academicYears, setAcademicYears] = useState<any[]>([]);
  const [terms, setTerms] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [school, setSchool] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Forms
  const [yearForm, setYearForm] = useState({ name: '', startDate: '', endDate: '' });
  const [termForm, setTermForm] = useState({ name: '', academicYearId: '', startDate: '', endDate: '' });
  const [deptForm, setDeptForm] = useState({ name: '', description: '' });
  const [showYearForm, setShowYearForm] = useState(false);
  const [showTermForm, setShowTermForm] = useState(false);
  const [showDeptForm, setShowDeptForm] = useState(false);

  useEffect(() => {
    loadTab(tab);
  }, [tab]);

  const loadTab = async (t: Tab) => {
    setLoading(true);
    try {
      if (t === 'academic-years') {
        const r = await apiClient.get('/settings/academic-years');
        setAcademicYears(r.data?.data || []);
      } else if (t === 'terms') {
        const [y, tr] = await Promise.all([apiClient.get('/settings/academic-years'), apiClient.get('/settings/terms')]);
        setAcademicYears(y.data?.data || []);
        setTerms(tr.data?.data || []);
      } else if (t === 'departments') {
        const r = await apiClient.get('/settings/departments');
        setDepartments(r.data?.data || []);
      } else if (t === 'notifications') {
        const r = await apiClient.get('/settings/notification-templates');
        setTemplates(r.data?.data || []);
      } else if (t === 'school-info') {
        const r = await apiClient.get('/customization/branding');
        setSchool(r.data?.data?.school || {});
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const createYear = async () => {
    if (!yearForm.name || !yearForm.startDate || !yearForm.endDate) return alert('All fields required');
    setSaving(true);
    try {
      await apiClient.post('/settings/academic-years', yearForm);
      setShowYearForm(false);
      setYearForm({ name: '', startDate: '', endDate: '' });
      loadTab('academic-years');
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const createTerm = async () => {
    if (!termForm.name || !termForm.academicYearId) return alert('Name and academic year required');
    setSaving(true);
    try {
      await apiClient.post('/settings/terms', termForm);
      setShowTermForm(false);
      setTermForm({ name: '', academicYearId: '', startDate: '', endDate: '' });
      loadTab('terms');
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const createDept = async () => {
    if (!deptForm.name) return alert('Name required');
    setSaving(true);
    try {
      await apiClient.post('/settings/departments', deptForm);
      setShowDeptForm(false);
      setDeptForm({ name: '', description: '' });
      loadTab('departments');
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const deleteDept = async (id: string) => {
    if (!confirm('Delete this department?')) return;
    await apiClient.delete(`/settings/departments/${id}`);
    loadTab('departments');
  };

  const TABS = [
    { key: 'academic-years' as Tab, label: '📅 Academic Years' },
    { key: 'terms' as Tab, label: '📆 Terms / Semesters' },
    { key: 'departments' as Tab, label: '🏢 Departments' },
    { key: 'notifications' as Tab, label: '🔔 Notification Templates' },
    { key: 'school-info' as Tab, label: '🏫 School Info' },
    { key: 'payments' as Tab, label: '💳 Payments' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
        <p className="text-sm text-gray-500">Configure academic structure, departments, and system preferences</p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 bg-gray-100 p-1 rounded-lg">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Academic Years */}
      {tab === 'academic-years' && (
        <div className="space-y-4">
          <div className="flex justify-end"><Button onClick={() => setShowYearForm(true)}>+ New Academic Year</Button></div>
          {showYearForm && (
            <Card className="p-4">
              <h3 className="font-semibold mb-3">New Academic Year</h3>
              <div className="grid grid-cols-3 gap-3">
                <Input placeholder="Name (e.g. 2024/2025)" value={yearForm.name} onChange={e => setYearForm(f => ({ ...f, name: e.target.value }))} />
                <Input type="date" value={yearForm.startDate} onChange={e => setYearForm(f => ({ ...f, startDate: e.target.value }))} />
                <Input type="date" value={yearForm.endDate} onChange={e => setYearForm(f => ({ ...f, endDate: e.target.value }))} />
              </div>
              <div className="flex gap-3 mt-3">
                <Button variant="outline" onClick={() => setShowYearForm(false)}>Cancel</Button>
                <Button onClick={createYear} disabled={saving}>{saving ? 'Saving...' : 'Create'}</Button>
              </div>
            </Card>
          )}
          <Card>
            {loading ? <div className="p-8 text-center text-gray-400">Loading...</div> :
              academicYears.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">📅</div>
                  <p>No academic years set up yet</p>
                  <Button className="mt-4" onClick={() => setShowYearForm(true)}>Create first academic year</Button>
                </div>
              ) : (
                <div className="divide-y">
                  {academicYears.map(y => (
                    <div key={y.id} className="px-5 py-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-semibold">{y.name}</p>
                          {y.isCurrent && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Current</span>}
                        </div>
                        <p className="text-sm text-gray-500">
                          {y.startDate ? new Date(y.startDate).toLocaleDateString() : '—'} → {y.endDate ? new Date(y.endDate).toLocaleDateString() : '—'}
                        </p>
                      </div>
                      {!y.isCurrent && (
                        <Button size="sm" variant="outline" onClick={async () => {
                          await apiClient.put(`/settings/academic-years/${y.id}`, { isCurrent: true });
                          loadTab('academic-years');
                        }}>Set Current</Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
          </Card>
        </div>
      )}

      {/* Terms */}
      {tab === 'terms' && (
        <div className="space-y-4">
          <div className="flex justify-end"><Button onClick={() => setShowTermForm(true)}>+ New Term</Button></div>
          {showTermForm && (
            <Card className="p-4">
              <h3 className="font-semibold mb-3">New Term / Semester</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Input placeholder="Term name (e.g. First Term)" value={termForm.name} onChange={e => setTermForm(f => ({ ...f, name: e.target.value }))} />
                <select className="border rounded-lg px-3 py-2 text-sm" value={termForm.academicYearId} onChange={e => setTermForm(f => ({ ...f, academicYearId: e.target.value }))}>
                  <option value="">Select Academic Year</option>
                  {academicYears.map(y => <option key={y.id} value={y.id}>{y.name}</option>)}
                </select>
                <Input type="date" value={termForm.startDate} onChange={e => setTermForm(f => ({ ...f, startDate: e.target.value }))} />
                <Input type="date" value={termForm.endDate} onChange={e => setTermForm(f => ({ ...f, endDate: e.target.value }))} />
              </div>
              <div className="flex gap-3 mt-3">
                <Button variant="outline" onClick={() => setShowTermForm(false)}>Cancel</Button>
                <Button onClick={createTerm} disabled={saving}>{saving ? 'Saving...' : 'Create Term'}</Button>
              </div>
            </Card>
          )}
          <Card>
            {loading ? <div className="p-8 text-center text-gray-400">Loading...</div> :
              terms.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">📆</div>
                  <p>No terms configured</p>
                  <Button className="mt-4" onClick={() => setShowTermForm(true)}>Create first term</Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b"><tr>
                      <th className="px-4 py-3 text-left">Term</th>
                      <th className="px-4 py-3 text-left">Academic Year</th>
                      <th className="px-4 py-3 text-left">Start</th>
                      <th className="px-4 py-3 text-left">End</th>
                    </tr></thead>
                    <tbody>
                      {terms.map(t => (
                        <tr key={t.id} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium">{t.name}</td>
                          <td className="px-4 py-3 text-gray-500">{t.academicYear?.name}</td>
                          <td className="px-4 py-3 text-gray-500">{t.startDate ? new Date(t.startDate).toLocaleDateString() : '—'}</td>
                          <td className="px-4 py-3 text-gray-500">{t.endDate ? new Date(t.endDate).toLocaleDateString() : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </Card>
        </div>
      )}

      {/* Departments */}
      {tab === 'departments' && (
        <div className="space-y-4">
          <div className="flex justify-end"><Button onClick={() => setShowDeptForm(true)}>+ New Department</Button></div>
          {showDeptForm && (
            <Card className="p-4">
              <h3 className="font-semibold mb-3">New Department</h3>
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Department name" value={deptForm.name} onChange={e => setDeptForm(f => ({ ...f, name: e.target.value }))} />
                <Input placeholder="Description (optional)" value={deptForm.description} onChange={e => setDeptForm(f => ({ ...f, description: e.target.value }))} />
              </div>
              <div className="flex gap-3 mt-3">
                <Button variant="outline" onClick={() => setShowDeptForm(false)}>Cancel</Button>
                <Button onClick={createDept} disabled={saving}>{saving ? 'Saving...' : 'Create'}</Button>
              </div>
            </Card>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loading ? <div className="col-span-3 text-center text-gray-400 py-12">Loading...</div> :
              departments.length === 0 ? (
                <Card className="col-span-3 p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">🏢</div>
                  <p>No departments created yet</p>
                  <Button className="mt-4" onClick={() => setShowDeptForm(true)}>Create first department</Button>
                </Card>
              ) : departments.map(d => (
                <Card key={d.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{d.name}</p>
                      {d.description && <p className="text-sm text-gray-500 mt-0.5">{d.description}</p>}
                      {d._count && <p className="text-xs text-gray-400 mt-1">{d._count.staff || 0} staff members</p>}
                    </div>
                    <button onClick={() => deleteDept(d.id)} className="text-red-400 hover:text-red-600 text-xs">Delete</button>
                  </div>
                </Card>
              ))}
          </div>
        </div>
      )}

      {/* Notification Templates */}
      {tab === 'notifications' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => window.location.href = '/dashboard/communications'}>Manage Templates →</Button>
          </div>
          <Card>
            {loading ? <div className="p-8 text-center text-gray-400">Loading...</div> :
              templates.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">🔔</div>
                  <p>No notification templates yet</p>
                  <p className="text-sm mt-1">Create templates in the Communications Center</p>
                  <Button className="mt-4" onClick={() => window.location.href = '/dashboard/communications'}>Go to Communications</Button>
                </div>
              ) : (
                <div className="divide-y">
                  {templates.map(t => (
                    <div key={t.id} className="px-5 py-4">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium">{t.name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${t.type === 'EMAIL' ? 'bg-blue-100 text-blue-700' : t.type === 'SMS' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>{t.type}</span>
                      </div>
                      {t.subject && <p className="text-sm text-gray-600">Subject: {t.subject}</p>}
                      <p className="text-sm text-gray-400 mt-1 line-clamp-2">{t.body}</p>
                    </div>
                  ))}
                </div>
              )}
          </Card>
        </div>
      )}

      {/* School Info */}
      {tab === 'school-info' && (
        <Card className="p-6 max-w-xl">
          <h2 className="font-semibold mb-4">School Information</h2>
          <div className="space-y-3">
            {[
              { label: 'School Name', key: 'name', placeholder: 'Enter school name' },
              { label: 'Address', key: 'address', placeholder: 'School address' },
              { label: 'Phone', key: 'phone', placeholder: '+234 800 000 0000' },
              { label: 'Email', key: 'email', placeholder: 'admin@school.edu' },
              { label: 'Website', key: 'website', placeholder: 'https://school.edu' },
            ].map(f => (
              <div key={f.key}>
                <label className="text-sm font-medium">{f.label}</label>
                <Input className="mt-1" placeholder={f.placeholder} value={school?.[f.key] || ''} onChange={e => setSchool((s: any) => ({ ...s, [f.key]: e.target.value }))} />
              </div>
            ))}
            <Button onClick={async () => {
              setSaving(true);
              try { await apiClient.put('/customization/branding', school); alert('Saved!'); }
              catch (e) { alert('Save failed'); }
              finally { setSaving(false); }
            }} disabled={saving} className="w-full">{saving ? 'Saving...' : '💾 Save School Info'}</Button>
          </div>
        </Card>
      )}

      {/* Payments redirect */}
      {tab === 'payments' && (
        <Card className="p-6">
          <h2 className="font-semibold mb-2">Payment Gateway Configuration</h2>
          <p className="text-sm text-gray-500 mb-4">Configure payment gateways, API keys, and webhook settings.</p>
          <Button onClick={() => window.location.href = '/dashboard/finance'}>Go to Finance Settings →</Button>
        </Card>
      )}
    </div>
  );
}
