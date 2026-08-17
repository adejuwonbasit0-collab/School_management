'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Role {
  id: string;
  name: string;
  description?: string;
  isSystem: boolean;
  isActive: boolean;
  permissions: { id: string; module: string; resource: string; action: string }[];
  _count?: { users: number };
}

type PermMatrix = Record<string, string[]>;

export default function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [matrix, setMatrix] = useState<PermMatrix>({});
  const [selected, setSelected] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', permissions: [] as string[] });

  useEffect(() => {
    Promise.all([
      apiClient.get('/settings/roles'),
      apiClient.get('/settings/roles/permissions-matrix'),
    ]).then(([r, m]) => {
      setRoles(r.data?.data || []);
      setMatrix(m.data?.data || {});
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const reload = async () => {
    const res = await apiClient.get('/settings/roles');
    setRoles(res.data?.data || []);
  };

  const openCreate = () => {
    setEditMode(false);
    setForm({ name: '', description: '', permissions: [] });
    setShowForm(true);
  };

  const openEdit = (role: Role) => {
    setEditMode(true);
    setForm({
      name: role.name,
      description: role.description || '',
      permissions: role.permissions.map(p => `${p.module}:${p.resource}:${p.action}`),
    });
    setSelected(role);
    setShowForm(true);
  };

  const save = async () => {
    if (!form.name.trim()) return alert('Role name required');
    setSaving(true);
    try {
      if (editMode && selected) {
        await apiClient.put(`/settings/roles/${selected.id}`, form);
      } else {
        await apiClient.post('/settings/roles', form);
      }
      setShowForm(false);
      await reload();
    } catch (e: any) { alert(e?.response?.data?.message || 'Save failed'); }
    finally { setSaving(false); }
  };

  const cloneRole = async (role: Role) => {
    const name = prompt(`Clone name:`, `${role.name} (Copy)`);
    if (!name) return;
    await apiClient.post(`/settings/roles/${role.id}/clone`, { name });
    await reload();
  };

  const toggleRole = async (role: Role) => {
    await apiClient.patch(`/settings/roles/${role.id}/toggle`, { isActive: !role.isActive });
    await reload();
  };

  const deleteRole = async (id: string) => {
    if (!confirm('Delete this role? Users with this role will lose access.')) return;
    try {
      await apiClient.delete(`/settings/roles/${id}`);
      setSelected(null);
      await reload();
    } catch (e: any) { alert(e?.response?.data?.message || 'Delete failed'); }
  };

  const togglePermission = (perm: string) => {
    setForm(f => ({
      ...f,
      permissions: f.permissions.includes(perm)
        ? f.permissions.filter(p => p !== perm)
        : [...f.permissions, perm],
    }));
  };

  const toggleModule = (perms: string[]) => {
    const allSelected = perms.every(p => form.permissions.includes(p));
    setForm(f => ({
      ...f,
      permissions: allSelected
        ? f.permissions.filter(p => !perms.includes(p))
        : [...new Set([...f.permissions, ...perms])],
    }));
  };

  const ACTION_COLORS: Record<string, string> = {
    READ: 'bg-blue-100 text-blue-700',
    CREATE: 'bg-green-100 text-green-700',
    UPDATE: 'bg-yellow-100 text-yellow-700',
    DELETE: 'bg-red-100 text-red-700',
    MANAGE: 'bg-purple-100 text-purple-700',
    APPROVE: 'bg-teal-100 text-teal-700',
    EXPORT: 'bg-indigo-100 text-indigo-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Roles & Permissions</h1>
          <p className="text-sm text-gray-500">Manage access control for every role in your school</p>
        </div>
        <Button onClick={openCreate}>+ New Role</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Role list */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            {roles.length} Roles
          </p>
          {loading ? (
            <div className="text-center text-gray-400 py-8">Loading roles...</div>
          ) : roles.map(role => (
            <div
              key={role.id}
              onClick={() => setSelected(role)}
              className={`rounded-lg border p-3 cursor-pointer hover:border-blue-300 transition-colors ${selected?.id === role.id ? 'border-blue-500 bg-blue-50' : 'bg-white'}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{role.name}</p>
                    {role.isSystem && <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">System</span>}
                    {!role.isActive && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">Disabled</span>}
                  </div>
                  {role.description && <p className="text-xs text-gray-400 mt-0.5">{role.description}</p>}
                  <p className="text-xs text-gray-400 mt-1">
                    {role._count?.users || 0} users · {role.permissions.length} permissions
                  </p>
                </div>
              </div>
              {selected?.id === role.id && (
                <div className="flex gap-1 mt-2" onClick={e => e.stopPropagation()}>
                  {!role.isSystem && <Button size="sm" variant="outline" onClick={() => openEdit(role)}>Edit</Button>}
                  <Button size="sm" variant="outline" onClick={() => cloneRole(role)}>Clone</Button>
                  {!role.isSystem && <Button size="sm" variant="outline" onClick={() => toggleRole(role)} className={role.isActive ? 'text-orange-600' : 'text-green-600'}>{role.isActive ? 'Disable' : 'Enable'}</Button>}
                  {!role.isSystem && <Button size="sm" variant="outline" onClick={() => deleteRole(role.id)} className="text-red-600">Delete</Button>}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Role permissions detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <Card className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-lg">{selected.name}</h2>
                {!selected.isSystem && <Button size="sm" onClick={() => openEdit(selected)}>Edit Permissions</Button>}
              </div>
              <div className="space-y-4">
                {Object.entries(matrix).map(([module, perms]) => {
                  const activePerms = perms.filter(p => selected.permissions.some(sp => `${sp.module}:${sp.resource}:${sp.action}` === p));
                  if (activePerms.length === 0) return null;
                  return (
                    <div key={module}>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 capitalize">{module}</p>
                      <div className="flex flex-wrap gap-2">
                        {activePerms.map(p => {
                          const action = p.split(':')[2];
                          return (
                            <span key={p} className={`text-xs px-2 py-1 rounded font-medium ${ACTION_COLORS[action] || 'bg-gray-100 text-gray-600'}`}>
                              {action}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
                {selected.permissions.length === 0 && (
                  <div className="text-center text-gray-400 py-8">No permissions assigned</div>
                )}
              </div>
            </Card>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-300">
              <div className="text-center"><div className="text-5xl mb-3">🔑</div><p>Select a role to view permissions</p></div>
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="p-5 border-b flex items-center justify-between">
              <h2 className="text-lg font-bold">{editMode ? 'Edit Role' : 'Create New Role'}</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="p-5 overflow-y-auto flex-1 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="text-sm font-medium">Role Name *</label><Input className="mt-1" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. Head of Department" /></div>
                <div><label className="text-sm font-medium">Description</label><Input className="mt-1" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Optional description" /></div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium">Permissions</label>
                  <div className="flex gap-2">
                    <button onClick={() => setForm(f => ({ ...f, permissions: Object.values(matrix).flat() }))} className="text-xs text-blue-600 hover:underline">Select All</button>
                    <span className="text-gray-300">|</span>
                    <button onClick={() => setForm(f => ({ ...f, permissions: [] }))} className="text-xs text-red-500 hover:underline">Clear All</button>
                  </div>
                </div>
                <div className="space-y-4">
                  {Object.entries(matrix).map(([module, perms]) => {
                    const allSelected = perms.every(p => form.permissions.includes(p));
                    const someSelected = perms.some(p => form.permissions.includes(p));
                    return (
                      <div key={module} className="border rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <input
                            type="checkbox"
                            checked={allSelected}
                            ref={el => { if (el) el.indeterminate = someSelected && !allSelected; }}
                            onChange={() => toggleModule(perms)}
                            className="w-4 h-4 cursor-pointer"
                          />
                          <span className="font-medium text-sm capitalize">{module}</span>
                          <span className="text-xs text-gray-400">({perms.filter(p => form.permissions.includes(p)).length}/{perms.length})</span>
                        </div>
                        <div className="flex flex-wrap gap-2 ml-6">
                          {perms.map(p => {
                            const action = p.split(':')[2];
                            const checked = form.permissions.includes(p);
                            return (
                              <label key={p} className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded cursor-pointer border transition-colors ${checked ? ACTION_COLORS[action] || 'bg-gray-100' : 'bg-white text-gray-500 border-gray-200'}`}>
                                <input type="checkbox" checked={checked} onChange={() => togglePermission(p)} className="w-3 h-3" />
                                {action}
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="p-5 border-t flex gap-3">
              <div className="text-sm text-gray-500 flex items-center">{form.permissions.length} permissions selected</div>
              <div className="flex-1" />
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={save} disabled={saving}>{saving ? 'Saving...' : editMode ? 'Update Role' : 'Create Role'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
