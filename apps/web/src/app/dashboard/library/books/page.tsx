'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LibraryBooksPage() {
  const [books, setBooks] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ title: '', author: '', isbn: '', category: '', quantity: 1, shelf: '', description: '', publishYear: '', publisher: '' });

  useEffect(() => {
    load();
    apiClient.get('/library/stats').then(r => setStats(r.data?.data)).catch(console.error);
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/library/books');
      setBooks(res.data?.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const save = async () => {
    if (!form.title || !form.author) return alert('Title and author required');
    setSaving(true);
    try {
      await apiClient.post('/library/books', form);
      setShowForm(false);
      setForm({ title: '', author: '', isbn: '', category: '', quantity: 1, shelf: '', description: '', publishYear: '', publisher: '' });
      load();
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const deleteBook = async (id: string) => {
    if (!confirm('Delete this book?')) return;
    await apiClient.delete(`/library/books/${id}`);
    load();
  };

  const filtered = books.filter(b => !search ||
    b.title?.toLowerCase().includes(search.toLowerCase()) ||
    b.author?.toLowerCase().includes(search.toLowerCase()) ||
    b.isbn?.includes(search)
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Library — Book Inventory</h1>
          <p className="text-sm text-gray-500">Manage books, categories, and shelves</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => window.location.href = '/dashboard/library/borrowing'}>📋 Borrowing</Button>
          <Button onClick={() => setShowForm(true)}>+ Add Book</Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Total Books</p><p className="text-3xl font-bold text-blue-600">{stats.totalBooks || books.length}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Available</p><p className="text-3xl font-bold text-green-600">{stats.available || 0}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Borrowed</p><p className="text-3xl font-bold text-orange-600">{stats.borrowed || 0}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Overdue</p><p className="text-3xl font-bold text-red-600">{stats.overdue || 0}</p></Card>
        </div>
      )}

      <div className="flex gap-3">
        <Input placeholder="Search by title, author, or ISBN..." value={search} onChange={e => setSearch(e.target.value)} className="max-w-md" />
      </div>

      <Card>
        {loading ? <div className="p-12 text-center text-gray-400">Loading books...</div> :
          filtered.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">📚</div>
              <p>{search ? 'No books match your search' : 'No books in the library yet'}</p>
              {!search && <Button className="mt-4" onClick={() => setShowForm(true)}>Add first book</Button>}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left">Title</th>
                    <th className="px-4 py-3 text-left">Author</th>
                    <th className="px-4 py-3 text-left">ISBN</th>
                    <th className="px-4 py-3 text-left">Category</th>
                    <th className="px-4 py-3 text-center">Qty</th>
                    <th className="px-4 py-3 text-center">Available</th>
                    <th className="px-4 py-3 text-left">Shelf</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(book => (
                    <tr key={book.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-900">{book.title}</p>
                        {book.publisher && <p className="text-xs text-gray-400">{book.publisher}</p>}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{book.author}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{book.isbn || '—'}</td>
                      <td className="px-4 py-3">
                        {book.category && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{book.category}</span>}
                      </td>
                      <td className="px-4 py-3 text-center font-medium">{book.quantity}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-medium ${(book.availableQuantity || book.quantity) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {book.availableQuantity ?? book.quantity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{book.shelf || '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <button onClick={() => deleteBook(book.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">Add Book</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-sm font-medium">Title *</label><Input className="mt-1" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
                <div><label className="text-sm font-medium">Author *</label><Input className="mt-1" value={form.author} onChange={e => setForm(f => ({ ...f, author: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-sm font-medium">ISBN</label><Input className="mt-1" value={form.isbn} onChange={e => setForm(f => ({ ...f, isbn: e.target.value }))} /></div>
                <div><label className="text-sm font-medium">Category</label><Input className="mt-1" placeholder="e.g. Science, Fiction" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div><label className="text-sm font-medium">Quantity</label><Input className="mt-1" type="number" min={1} value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: +e.target.value }))} /></div>
                <div><label className="text-sm font-medium">Shelf</label><Input className="mt-1" placeholder="e.g. A1" value={form.shelf} onChange={e => setForm(f => ({ ...f, shelf: e.target.value }))} /></div>
                <div><label className="text-sm font-medium">Year</label><Input className="mt-1" placeholder="2024" value={form.publishYear} onChange={e => setForm(f => ({ ...f, publishYear: e.target.value }))} /></div>
              </div>
              <div><label className="text-sm font-medium">Publisher</label><Input className="mt-1" value={form.publisher} onChange={e => setForm(f => ({ ...f, publisher: e.target.value }))} /></div>
              <div><label className="text-sm font-medium">Description</label><textarea className="w-full mt-1 border rounded-lg px-3 py-2 text-sm resize-none" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Add Book'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
