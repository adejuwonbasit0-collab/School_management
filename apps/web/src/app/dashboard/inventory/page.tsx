'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'items' | 'assets' | 'suppliers' | 'low-stock';

export default function InventoryPage() {
  const [tab, setTab] = useState<Tab>('items');
  const [items, setItems] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [lowStock, setLowStock] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showTx, setShowTx] = useState<any>(null);
  const [form, setForm] = useState({ name: '', categoryId: '', unit: 'unit', quantityInStock: 0, reorderLevel: 5, unitCost: 0, isAsset: false, description: '' });
  const [txForm, setTxForm] = useState({ type: 'IN', quantity: 1, notes: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiClient.get('/inventory/stats').then(r => setStats(r.data?.data)).catch(console.error);
    apiClient.get('/inventory/categories').then(r => setCategories(r.data?.data || [])).catch(console.error);
    apiClient.get('/inventory/suppliers').then(r => setSuppliers(r.data?.data || [])).catch(console.error);
    apiClient.get('/inventory/low-stock').then(r => setLowStock(r.data?.data || [])).catch(console.error);
  }, []);

  useEffect(() => { loadItems(); }, [tab]);

  const loadItems = async () => {
    setLoading(true);
    try {
      const isAsset = tab === 'assets' ? 'true' : tab === 'items' ? 'false' : undefined;
      const res = await apiClient.get(`/inventory/items${isAsset !== undefined ? `?isAsset=${isAsset}` : ''}`);
      setItems(res.data?.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const saveItem = async () => {
    setSaving(true);
    try {
      await apiClient.post('/inventory/items', { ...form, isAsset: tab === 'assets' });
      setShowForm(false);
      setForm({ name: '', categoryId: '', unit: 'unit', quantityInStock: 0, reorderLevel: 5, unitCost: 0, isAsset: false, description: '' });
      loadItems();
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const recordTransaction = async () => {
    if (!showTx) return;
    setSaving(true);
    try {
      await apiClient.post(`/inventory/items/${showTx.id}/transactions`, txForm);
      setShowTx(null);
      loadItems();
    } catch (e: any) { alert(e?.response?.data?.message || 'Transaction failed'); }
    finally { setSaving(false); }
  };

  const deleteItem = async (id: string) => {
    if (!confirm('Delete this item?')) return;
    try { await apiClient.delete(`/inventory/items/${id}`); loadItems(); }
    catch (e) { alert('Delete failed'); }
  };

  const filtered = items.filter(i => !search || i.name.toLowerCase().includes(search.toLowerCase()));

  const tabs: { key: Tab; label: string }[] = [
    { key: 'items', label: '📦 Inventory' },
    { key: 'assets', label: '🏷️ Assets' },
    { key: 'suppliers', label: '🏭 Suppliers' },
    { key: 'low-stock', label: `⚠️ Low Stock${lowStock.length > 0 ? ` (${lowStock.length})` : ''}` },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory & Assets</h1>
          <p className="text-sm text-gray-500">Track school equipment, supplies, and assets</p>
        </div>
        <Button onClick={() => setShowForm(true)}>+ Add {tab === 'assets' ? 'Asset' : 'Item'}</Button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Inventory Items</p><p className="text-3xl font-bold text-blue-600">{stats.totalItems}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Assets</p><p className="text-3xl font-bold text-purple-600">{stats.totalAssets}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Low Stock</p><p className="text-3xl font-bold text-red-600">{stats.lowStock}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Categories</p><p className="text-3xl font-bold text-green-600">{categories.length}</p></Card>
        </div>
      )}

      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Low Stock */}
      {tab === 'low-stock' && (
        <Card>
          {lowStock.length === 0 ? (
            <div className="p-12 text-center text-green-600"><div className="text-4xl mb-2">✅</div><p>All items are well stocked!</p></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="px-4 py-3 text-left">Item</th><th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-right">In Stock</th><th className="px-4 py-3 text-right">Reorder Level</th>
                </tr></thead>
                <tbody>{lowStock.map(i => (
                  <tr key={i.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-red-600">{i.name}</td>
                    <td className="px-4 py-3 text-gray-500">{i.category?.name || '—'}</td>
                    <td className="px-4 py-3 text-right font-bold text-red-600">{i.quantityInStock}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{i.reorderLevel}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Suppliers */}
      {tab === 'suppliers' && (
        <Card>
          <div className="p-4 border-b flex items-center justify-between">
            <span className="font-semibold">Suppliers</span>
            <Button size="sm" onClick={async () => {
              const name = prompt('Supplier name:');
              const email = prompt('Email (optional):');
              if (name) { await apiClient.post('/inventory/suppliers', { name, email }); apiClient.get('/inventory/suppliers').then(r => setSuppliers(r.data?.data || [])); }
            }}>+ Add Supplier</Button>
          </div>
          <div className="divide-y">
            {suppliers.length === 0 ? <div className="p-8 text-center text-gray-400">No suppliers yet</div> :
              suppliers.map(s => (
                <div key={s.id} className="px-4 py-3 flex items-center justify-between">
                  <div><p className="font-medium">{s.name}</p><p className="text-sm text-gray-500">{s.email} {s.phone && `· ${s.phone}`}</p></div>
                </div>
              ))}
          </div>
        </Card>
      )}

      {/* Items / Assets */}
      {(tab === 'items' || tab === 'assets') && (
        <>
          <div className="flex gap-3">
            <Input placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} className="max-w-xs" />
          </div>
          <Card>
            {loading ? <div className="p-12 text-center text-gray-400">Loading...</div> :
              filtered.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">{tab === 'assets' ? '🏷️' : '📦'}</div>
                  <p>No {tab === 'assets' ? 'assets' : 'items'} found</p>
                  <Button className="mt-4" onClick={() => setShowForm(true)}>Add first {tab === 'assets' ? 'asset' : 'item'}</Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b"><tr>
                      <th className="px-4 py-3 text-left">Name</th><th className="px-4 py-3 text-left">Category</th>
                      <th className="px-4 py-3 text-right">Qty</th><th className="px-4 py-3 text-right">Unit Cost</th>
                      <th className="px-4 py-3 text-left">Status</th><th className="px-4 py-3 text-left">Actions</th>
                    </tr></thead>
                    <tbody>{filtered.map(item => (
                      <tr key={item.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3"><p className="font-medium">{item.name}</p>{item.sku && <p className="text-xs text-gray-400">SKU: {item.sku}</p>}</td>
                        <td className="px-4 py-3 text-gray-500">{item.category?.name || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`font-semibold ${item.quantityInStock <= item.reorderLevel ? 'text-red-600' : 'text-gray-900'}`}>
                            {item.quantityInStock}
                          </span>
                          <span className="text-gray-400 text-xs ml-1">{item.unit}</span>
                        </td>
                        <td className="px-4 py-3 text-right">₦{Number(item.unitCost).toLocaleString()}</td>
                        <td className="px-4 py-3">
                          {item.quantityInStock <= item.reorderLevel
                            ? <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Low Stock</span>
                            : <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">In Stock</span>}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button onClick={() => { setShowTx(item); setTxForm({ type: 'IN', quantity: 1, notes: '' }); }}
                              className="text-blue-600 hover:underline text-xs">Stock In/Out</button>
                            <button onClick={() => deleteItem(item.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
          </Card>
        </>
      )}

      {/* Add Item Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Add {tab === 'assets' ? 'Asset' : 'Item'}</h2>
            <div className="space-y-3">
              <Input placeholder="Name *" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.categoryId} onChange={e => setForm(f => ({ ...f, categoryId: e.target.value }))}>
                <option value="">Select Category</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <Input type="number" placeholder="Qty" value={form.quantityInStock} onChange={e => setForm(f => ({ ...f, quantityInStock: +e.target.value }))} />
                <Input type="number" placeholder="Unit Cost" value={form.unitCost} onChange={e => setForm(f => ({ ...f, unitCost: +e.target.value }))} />
              </div>
              <Input placeholder="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={saveItem} disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction Modal */}
      {showTx && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-bold mb-1">Stock Transaction</h2>
            <p className="text-sm text-gray-500 mb-4">{showTx.name} · Current: {showTx.quantityInStock} {showTx.unit}</p>
            <div className="space-y-3">
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={txForm.type} onChange={e => setTxForm(f => ({ ...f, type: e.target.value }))}>
                <option value="IN">Stock In (Add)</option>
                <option value="OUT">Stock Out (Remove)</option>
                <option value="ADJUST">Adjust (Set absolute)</option>
              </select>
              <Input type="number" placeholder="Quantity" value={txForm.quantity} onChange={e => setTxForm(f => ({ ...f, quantity: +e.target.value }))} />
              <Input placeholder="Notes (optional)" value={txForm.notes} onChange={e => setTxForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowTx(null)}>Cancel</Button>
              <Button onClick={recordTransaction} disabled={saving}>{saving ? 'Saving...' : 'Record'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
