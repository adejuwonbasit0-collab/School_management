'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'payslips' | 'structures' | 'reviews';

export default function PayslipsPage() {
  const [tab, setTab] = useState<Tab>('payslips');
  const [payrolls, setPayrolls] = useState<any[]>([]);
  const [structures, setStructures] = useState<any[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showStructureForm, setShowStructureForm] = useState(false);
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const [structureForm, setStructureForm] = useState({
    name: '', basicSalary: 0,
    allowances: { housing: 10, transport: 5, medical: 5 },
    deductions: { tax: 7.5, pension: 8 },
    description: '', isDefault: false,
  });

  const [generateForm, setGenerateForm] = useState({
    staffId: '', month: new Date().getMonth() + 1, year: new Date().getFullYear(), notes: '',
  });

  useEffect(() => {
    loadData();
  }, [tab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (tab === 'payslips') {
        const res = await apiClient.get('/hr/payroll');
        setPayrolls(res.data?.data || res.data || []);
      } else if (tab === 'structures') {
        const [strRes, staffRes] = await Promise.all([
          apiClient.get('/hr/salary-structures'),
          apiClient.get('/hr/staff'),
        ]);
        setStructures(strRes.data?.data || []);
        setStaff(staffRes.data?.data?.data || []);
      } else if (tab === 'reviews') {
        const res = await apiClient.get('/hr/performance-reviews');
        setPayrolls(res.data?.data || []);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const saveStructure = async () => {
    setSaving(true);
    try {
      await apiClient.post('/hr/salary-structures', structureForm);
      setShowStructureForm(false);
      setStructureForm({ name: '', basicSalary: 0, allowances: { housing: 10, transport: 5, medical: 5 }, deductions: { tax: 7.5, pension: 8 }, description: '', isDefault: false });
      loadData();
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const generatePayslip = async () => {
    setSaving(true);
    try {
      await apiClient.post('/hr/payroll/generate', generateForm);
      setShowGenerateForm(false);
      setTab('payslips');
      loadData();
    } catch (e: any) { alert(e?.response?.data?.message || 'Generation failed'); }
    finally { setSaving(false); }
  };

  const downloadPayslip = (id: string) => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/hr/payroll/${id}/pdf`, '_blank');
  };

  const STATUS_COLORS: Record<string, string> = {
    PAID: 'bg-green-100 text-green-700',
    PENDING: 'bg-yellow-100 text-yellow-700',
    PROCESSING: 'bg-blue-100 text-blue-700',
  };

  const calcGross = (basic: number, allowances: any) => {
    const pct = Object.values(allowances as Record<string, number>).reduce((a, b) => a + b, 0);
    return basic + (basic * pct / 100);
  };

  const calcNet = (basic: number, allowances: any, deductions: any) => {
    const gross = calcGross(basic, allowances);
    const dedPct = Object.values(deductions as Record<string, number>).reduce((a, b) => a + b, 0);
    return gross - (basic * dedPct / 100);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payroll & HR Records</h1>
          <p className="text-sm text-gray-500">Manage salary structures, payslips, and performance reviews</p>
        </div>
        <div className="flex gap-2">
          {tab === 'payslips' && <Button onClick={() => setShowGenerateForm(true)}>+ Generate Payslip</Button>}
          {tab === 'structures' && <Button onClick={() => setShowStructureForm(true)}>+ New Salary Structure</Button>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'payslips' as Tab, label: '💰 Payslips' },
          { key: 'structures' as Tab, label: '📐 Salary Structures' },
          { key: 'reviews' as Tab, label: '⭐ Performance Reviews' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Payslips */}
      {tab === 'payslips' && (
        <Card>
          {loading ? <div className="p-12 text-center text-gray-400">Loading payslips...</div> :
            payrolls.length === 0 ? (
              <div className="p-12 text-center text-gray-400">
                <div className="text-4xl mb-3">💰</div>
                <p>No payslips generated yet</p>
                <Button className="mt-4" onClick={() => setShowGenerateForm(true)}>Generate first payslip</Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left">Staff</th>
                      <th className="px-4 py-3 text-left">Period</th>
                      <th className="px-4 py-3 text-right">Basic</th>
                      <th className="px-4 py-3 text-right">Gross</th>
                      <th className="px-4 py-3 text-right">Deductions</th>
                      <th className="px-4 py-3 text-right">Net Pay</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payrolls.map((p: any) => (
                      <tr key={p.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <p className="font-medium">{p.staff?.user?.firstName} {p.staff?.user?.lastName}</p>
                          <p className="text-xs text-gray-400">{p.staff?.staffId}</p>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {new Date(0, p.month - 1).toLocaleString('default', { month: 'long' })} {p.year}
                        </td>
                        <td className="px-4 py-3 text-right">₦{Number(p.basicSalary || 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right">₦{Number(p.grossSalary || 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-red-600">₦{Number(p.totalDeductions || 0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-bold text-green-600">₦{Number(p.netSalary || 0).toLocaleString()}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[p.status] || 'bg-gray-100'}`}>
                            {p.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button onClick={() => downloadPayslip(p.id)} className="text-blue-600 hover:underline text-xs">
                            📄 Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </Card>
      )}

      {/* Salary Structures */}
      {tab === 'structures' && (
        <div className="grid gap-4">
          {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
            structures.length === 0 ? (
              <Card className="p-12 text-center text-gray-400">
                <div className="text-4xl mb-3">📐</div>
                <p>No salary structures defined</p>
                <Button className="mt-4" onClick={() => setShowStructureForm(true)}>Create first structure</Button>
              </Card>
            ) : structures.map(s => (
              <Card key={s.id} className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg">{s.name}</h3>
                      {s.isDefault && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Default</span>}
                    </div>
                    {s.description && <p className="text-sm text-gray-500">{s.description}</p>}
                  </div>
                  <p className="text-2xl font-bold text-green-600">₦{Number(s.basicSalary).toLocaleString()}<span className="text-sm font-normal text-gray-500">/mo</span></p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="font-medium text-gray-700 mb-2">Allowances</p>
                    {Object.entries(s.allowances as Record<string, number>).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-gray-500 capitalize">{k}</span>
                        <span className="text-green-600">+{v}%</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <p className="font-medium text-gray-700 mb-2">Deductions</p>
                    {Object.entries(s.deductions as Record<string, number>).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-gray-500 capitalize">{k}</span>
                        <span className="text-red-500">-{v}%</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t flex justify-between text-sm font-medium">
                  <span>Estimated Net Pay</span>
                  <span className="text-blue-600">₦{calcNet(Number(s.basicSalary), s.allowances, s.deductions).toLocaleString()}</span>
                </div>
              </Card>
            ))}
        </div>
      )}

      {/* Performance Reviews */}
      {tab === 'reviews' && (
        <Card>
          <div className="p-4 border-b flex items-center justify-between">
            <span className="font-semibold">Performance Reviews</span>
            <Button size="sm" onClick={async () => {
              const staffId = prompt('Staff ID:');
              const period = prompt('Review period (e.g. Q1 2024):');
              if (!staffId || !period) return;
              await apiClient.post('/hr/performance-reviews', {
                staffId, period,
                scores: { punctuality: 80, teamwork: 85, performance: 90, communication: 75 },
                comments: 'Satisfactory performance overall.',
              });
              loadData();
            }}>+ Add Review</Button>
          </div>
          {loading ? (
            <div className="p-12 text-center text-gray-400">Loading reviews...</div>
          ) : payrolls.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">⭐</div>
              <p>No performance reviews yet</p>
            </div>
          ) : (
            <div className="divide-y">
              {payrolls.map((r: any) => (
                <div key={r.id} className="px-5 py-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{r.staff?.user?.firstName} {r.staff?.user?.lastName}</p>
                      <p className="text-sm text-gray-500">{r.period}</p>
                      {r.comments && <p className="text-sm text-gray-600 mt-1">{r.comments}</p>}
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-blue-600">{Number(r.totalScore).toFixed(0)}<span className="text-sm text-gray-400">/100</span></p>
                      {r.grade && <span className="text-sm font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{r.grade}</span>}
                    </div>
                  </div>
                  {r.scores && (
                    <div className="grid grid-cols-4 gap-3 mt-3">
                      {Object.entries(r.scores as Record<string, number>).map(([k, v]) => (
                        <div key={k} className="text-center">
                          <p className="text-xs text-gray-500 capitalize">{k}</p>
                          <p className="font-semibold text-gray-900">{v}</p>
                          <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
                            <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${v}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Salary Structure Form Modal */}
      {showStructureForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold mb-4">New Salary Structure</h2>
            <div className="space-y-4">
              <Input placeholder="Structure name (e.g. Senior Teacher)" value={structureForm.name} onChange={e => setStructureForm(f => ({ ...f, name: e.target.value }))} />
              <div>
                <label className="text-sm font-medium">Basic Salary (₦)</label>
                <Input type="number" value={structureForm.basicSalary} onChange={e => setStructureForm(f => ({ ...f, basicSalary: +e.target.value }))} />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Allowances (%)</label>
                <div className="grid grid-cols-3 gap-3">
                  {Object.keys(structureForm.allowances).map(k => (
                    <div key={k}>
                      <label className="text-xs text-gray-500 capitalize">{k}</label>
                      <Input type="number" step="0.5" value={(structureForm.allowances as any)[k]}
                        onChange={e => setStructureForm(f => ({ ...f, allowances: { ...f.allowances, [k]: +e.target.value } }))} />
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Deductions (%)</label>
                <div className="grid grid-cols-2 gap-3">
                  {Object.keys(structureForm.deductions).map(k => (
                    <div key={k}>
                      <label className="text-xs text-gray-500 capitalize">{k}</label>
                      <Input type="number" step="0.5" value={(structureForm.deductions as any)[k]}
                        onChange={e => setStructureForm(f => ({ ...f, deductions: { ...f.deductions, [k]: +e.target.value } }))} />
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg text-sm">
                <div className="flex justify-between"><span>Gross Salary:</span><span className="font-medium text-green-600">₦{calcGross(structureForm.basicSalary, structureForm.allowances).toLocaleString()}</span></div>
                <div className="flex justify-between mt-1"><span>Net Pay:</span><span className="font-bold text-blue-600">₦{calcNet(structureForm.basicSalary, structureForm.allowances, structureForm.deductions).toLocaleString()}</span></div>
              </div>
              <Input placeholder="Description (optional)" value={structureForm.description} onChange={e => setStructureForm(f => ({ ...f, description: e.target.value }))} />
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={structureForm.isDefault} onChange={e => setStructureForm(f => ({ ...f, isDefault: e.target.checked }))} />
                Set as default structure
              </label>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="outline" onClick={() => setShowStructureForm(false)}>Cancel</Button>
              <Button onClick={saveStructure} disabled={saving}>{saving ? 'Saving...' : 'Save Structure'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Payslip Modal */}
      {showGenerateForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Generate Payslip</h2>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Staff Member *</label>
                <select className="w-full border rounded-lg px-3 py-2 text-sm mt-1" value={generateForm.staffId} onChange={e => setGenerateForm(f => ({ ...f, staffId: e.target.value }))}>
                  <option value="">Select staff</option>
                  {staff.map((s: any) => (
                    <option key={s.id} value={s.id}>{s.user?.firstName} {s.user?.lastName} — {s.role}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">Month</label>
                  <select className="w-full border rounded-lg px-3 py-2 text-sm mt-1" value={generateForm.month} onChange={e => setGenerateForm(f => ({ ...f, month: +e.target.value }))}>
                    {Array.from({ length: 12 }, (_, i) => (
                      <option key={i + 1} value={i + 1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Year</label>
                  <Input type="number" value={generateForm.year} onChange={e => setGenerateForm(f => ({ ...f, year: +e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Notes</label>
                <Input placeholder="Optional notes" value={generateForm.notes} onChange={e => setGenerateForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="outline" onClick={() => setShowGenerateForm(false)}>Cancel</Button>
              <Button onClick={generatePayslip} disabled={saving || !generateForm.staffId}>{saving ? 'Generating...' : 'Generate Payslip'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
