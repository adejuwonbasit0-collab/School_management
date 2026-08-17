'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'active' | 'overdue' | 'history' | 'issue';

export default function BorrowingPage() {
  const [tab, setTab] = useState<Tab>('active');
  const [borrowings, setBorrowings] = useState<any[]>([]);
  const [books, setBooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [issueForm, setIssueForm] = useState({ bookId: '', studentId: '', dueDate: '', notes: '' });
  const [saving, setSaving] = useState(false);

  const daysFromNow = (n: number) => {
    const d = new Date();
    d.setDate(d.getDate() + n);
    return d.toISOString().split('T')[0];
  };

  useEffect(() => {
    apiClient.get('/library/books').then(r => setBooks(r.data?.data?.data || [])).catch(console.error);
    loadBorrowings();
  }, [tab]);

  const loadBorrowings = async () => {
    setLoading(true);
    try {
      const status = tab === 'active' ? 'BORROWED' : tab === 'overdue' ? 'OVERDUE' : tab === 'history' ? 'RETURNED' : undefined;
      const url = status ? `/library/borrowings?status=${status}` : '/library/borrowings';
      const res = await apiClient.get(url);
      setBorrowings(res.data?.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const issueBorrow = async () => {
    if (!issueForm.bookId || !issueForm.studentId || !issueForm.dueDate) return alert('Book, student, and due date required');
    setSaving(true);
    try {
      await apiClient.post('/library/borrowings', issueForm);
      setIssueForm({ bookId: '', studentId: '', dueDate: daysFromNow(14), notes: '' });
      setTab('active');
    } catch (e: any) { alert(e?.response?.data?.message || 'Issue failed'); }
    finally { setSaving(false); }
  };

  const returnBook = async (id: string) => {
    try {
      await apiClient.put(`/library/borrowings/${id}/return`);
      loadBorrowings();
    } catch (e: any) { alert(e?.response?.data?.message || 'Return failed'); }
  };

  const TABS = [
    { key: 'active' as Tab, label: '📖 Active' },
    { key: 'overdue' as Tab, label: '⏰ Overdue' },
    { key: 'history' as Tab, label: '📋 History' },
    { key: 'issue' as Tab, label: '+ Issue Book' },
  ];

  const STATUS_COLORS: Record<string, string> = {
    BORROWED: 'bg-blue-100 text-blue-700',
    OVERDUE: 'bg-red-100 text-red-700',
    RETURNED: 'bg-green-100 text-green-700',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Library — Borrowing</h1>
        <p className="text-sm text-gray-500">Issue, return, and track book borrowings</p>
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Issue book form */}
      {tab === 'issue' && (
        <Card className="p-6 max-w-lg">
          <h2 className="font-semibold mb-4">Issue Book to Student</h2>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Book *</label>
              <select className="w-full mt-1 border rounded-lg px-3 py-2 text-sm" value={issueForm.bookId} onChange={e => setIssueForm(f => ({ ...f, bookId: e.target.value }))}>
                <option value="">Select book</option>
                {books.filter(b => (b.availableQuantity ?? b.quantity) > 0).map(b => (
                  <option key={b.id} value={b.id}>{b.title} by {b.author} (Available: {b.availableQuantity ?? b.quantity})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Student ID *</label>
              <Input className="mt-1" placeholder="Enter student ID" value={issueForm.studentId} onChange={e => setIssueForm(f => ({ ...f, studentId: e.target.value }))} />
            </div>
            <div>
              <label className="text-sm font-medium">Due Date *</label>
              <Input className="mt-1" type="date" min={new Date().toISOString().split('T')[0]} value={issueForm.dueDate || daysFromNow(14)} onChange={e => setIssueForm(f => ({ ...f, dueDate: e.target.value }))} />
            </div>
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Input className="mt-1" placeholder="Optional notes" value={issueForm.notes} onChange={e => setIssueForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <Button onClick={issueBorrow} disabled={saving} className="w-full">{saving ? 'Issuing...' : '📖 Issue Book'}</Button>
          </div>
        </Card>
      )}

      {/* Borrowings list */}
      {tab !== 'issue' && (
        <Card>
          {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
            borrowings.length === 0 ? (
              <div className="p-12 text-center text-gray-400">
                <div className="text-4xl mb-3">{tab === 'overdue' ? '✅' : '📚'}</div>
                <p>{tab === 'overdue' ? 'No overdue books!' : `No ${tab} borrowings`}</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left">Book</th>
                      <th className="px-4 py-3 text-left">Student</th>
                      <th className="px-4 py-3 text-left">Issued</th>
                      <th className="px-4 py-3 text-left">Due Date</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      {tab !== 'history' && <th className="px-4 py-3 text-left">Fine</th>}
                      <th className="px-4 py-3 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {borrowings.map(b => {
                      const due = new Date(b.dueDate);
                      const now = new Date();
                      const daysOverdue = Math.max(0, Math.floor((now.getTime() - due.getTime()) / (1000 * 60 * 60 * 24)));
                      const fine = daysOverdue * (b.finePerDay || 50);
                      return (
                        <tr key={b.id} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <p className="font-medium">{b.book?.title}</p>
                            <p className="text-xs text-gray-400">{b.book?.author}</p>
                          </td>
                          <td className="px-4 py-3 text-gray-600">
                            {b.student?.user?.firstName} {b.student?.user?.lastName}
                          </td>
                          <td className="px-4 py-3 text-gray-500">{new Date(b.borrowedAt || b.createdAt).toLocaleDateString()}</td>
                          <td className="px-4 py-3">
                            <span className={daysOverdue > 0 ? 'text-red-600 font-medium' : 'text-gray-600'}>
                              {due.toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[b.status] || 'bg-gray-100'}`}>
                              {b.status}
                            </span>
                          </td>
                          {tab !== 'history' && (
                            <td className="px-4 py-3">
                              {fine > 0 ? <span className="text-red-600 font-medium">₦{fine}</span> : <span className="text-gray-400">—</span>}
                            </td>
                          )}
                          <td className="px-4 py-3">
                            {b.status !== 'RETURNED' && (
                              <Button size="sm" onClick={() => returnBook(b.id)}>Return</Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
        </Card>
      )}
    </div>
  );
}
