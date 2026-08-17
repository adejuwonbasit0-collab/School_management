'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function TransportRoutesPage() {
  const [routes, setRoutes] = useState<any[]>([]);
  const [buses, setBuses] = useState<any[]>([]);
  const [drivers, setDrivers] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showPickupForm, setShowPickupForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [routeForm, setRouteForm] = useState({ name: '', description: '', busId: '', driverId: '' });
  const [pickupForm, setPickupForm] = useState({ name: '', time: '', landmark: '', sequence: 1 });

  useEffect(() => {
    Promise.all([
      apiClient.get('/transport/routes').catch(() => ({ data: [] })),
      apiClient.get('/transport/buses').catch(() => ({ data: [] })),
      apiClient.get('/transport/drivers').catch(() => ({ data: [] })),
    ]).then(([r, b, d]) => {
      setRoutes(r.data?.data || r.data || []);
      setBuses(b.data?.data || b.data || []);
      setDrivers(d.data?.data || d.data || []);
    }).finally(() => setLoading(false));
  }, []);

  const createRoute = async () => {
    if (!routeForm.name) return alert('Route name required');
    setSaving(true);
    try {
      await apiClient.post('/transport/routes', routeForm);
      setShowForm(false);
      setRouteForm({ name: '', description: '', busId: '', driverId: '' });
      const res = await apiClient.get('/transport/routes');
      setRoutes(res.data?.data || res.data || []);
    } catch (e) { alert('Failed to create route'); }
    finally { setSaving(false); }
  };

  const deleteRoute = async (id: string) => {
    if (!confirm('Delete this route?')) return;
    await apiClient.delete(`/transport/routes/${id}`);
    setSelected(null);
    const res = await apiClient.get('/transport/routes');
    setRoutes(res.data?.data || res.data || []);
  };

  const addPickup = async () => {
    if (!selected || !pickupForm.name) return;
    setSaving(true);
    try {
      await apiClient.post(`/transport/routes/${selected.id}/pickup-points`, pickupForm);
      setShowPickupForm(false);
      setPickupForm({ name: '', time: '', landmark: '', sequence: (selected.pickupPoints?.length || 0) + 1 });
      const res = await apiClient.get(`/transport/routes/${selected.id}`);
      setSelected(res.data);
    } catch (e) { alert('Failed to add pickup point'); }
    finally { setSaving(false); }
  };

  const toggleRoute = async (id: string, isActive: boolean) => {
    await apiClient.put(`/transport/routes/${id}`, { isActive: !isActive });
    const res = await apiClient.get('/transport/routes');
    setRoutes(res.data?.data || res.data || []);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transport — Routes</h1>
          <p className="text-sm text-gray-500">Manage bus routes, pickup points, and driver assignments</p>
        </div>
        <Button onClick={() => setShowForm(true)}>+ New Route</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4"><p className="text-sm text-gray-500">Total Routes</p><p className="text-3xl font-bold text-blue-600">{routes.length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Active</p><p className="text-3xl font-bold text-green-600">{routes.filter(r => r.isActive).length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Buses</p><p className="text-3xl font-bold text-purple-600">{buses.length}</p></Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Routes list */}
        <div className="space-y-3">
          {loading ? <div className="text-center text-gray-400 py-12">Loading routes...</div> :
            routes.length === 0 ? (
              <Card className="p-12 text-center text-gray-400">
                <div className="text-4xl mb-3">🚌</div>
                <p>No routes configured yet</p>
                <Button className="mt-4" onClick={() => setShowForm(true)}>Create first route</Button>
              </Card>
            ) : routes.map(route => (
              <Card key={route.id} onClick={() => setSelected(route)}
                className={`p-4 cursor-pointer hover:border-blue-300 transition-colors ${selected?.id === route.id ? 'border-blue-500 bg-blue-50' : ''}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🚌</span>
                      <h3 className="font-semibold">{route.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${route.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {route.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    {route.description && <p className="text-sm text-gray-500 mt-1">{route.description}</p>}
                    <div className="flex gap-3 mt-1 text-xs text-gray-400">
                      <span>🚏 {route.pickupPoints?.length || 0} stops</span>
                      <span>👥 {route.assignments?.length || 0} students</span>
                    </div>
                  </div>
                </div>
                {selected?.id === route.id && (
                  <div className="flex gap-2 mt-3" onClick={e => e.stopPropagation()}>
                    <Button size="sm" variant="outline" onClick={() => setShowPickupForm(true)}>+ Stop</Button>
                    <Button size="sm" variant="outline" onClick={() => toggleRoute(route.id, route.isActive)}>
                      {route.isActive ? 'Deactivate' : 'Activate'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => deleteRoute(route.id)} className="text-red-600">Delete</Button>
                  </div>
                )}
              </Card>
            ))}
        </div>

        {/* Route detail */}
        {selected ? (
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold">📍 {selected.name} — Pickup Stops</h2>
              <Button size="sm" onClick={() => setShowPickupForm(true)}>+ Add Stop</Button>
            </div>
            {(selected.pickupPoints || []).length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                <div className="text-3xl mb-2">🚏</div>
                <p className="text-sm">No pickup points defined</p>
              </div>
            ) : (
              <div className="space-y-2">
                {(selected.pickupPoints || []).sort((a: any, b: any) => a.sequence - b.sequence).map((p: any, i: number) => (
                  <div key={p.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">{p.name}</p>
                      {p.landmark && <p className="text-xs text-gray-400">{p.landmark}</p>}
                    </div>
                    {p.time && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-medium">{p.time}</span>}
                  </div>
                ))}
              </div>
            )}

            {/* Bus & Driver info */}
            {(selected.busId || selected.driverId) && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm font-medium mb-2">Assignment</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {selected.busId && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-400">Bus</p><p className="font-medium">{buses.find(b => b.id === selected.busId)?.plateNumber || selected.busId}</p></div>}
                  {selected.driverId && <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-400">Driver</p><p className="font-medium">{drivers.find(d => d.id === selected.driverId)?.name || selected.driverId}</p></div>}
                </div>
              </div>
            )}
          </Card>
        ) : (
          <div className="hidden lg:flex items-center justify-center text-gray-300 h-64">
            <div className="text-center"><div className="text-5xl mb-3">🚌</div><p>Select a route to view details</p></div>
          </div>
        )}
      </div>

      {/* Create Route Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">New Route</h2>
            <div className="space-y-3">
              <Input placeholder="Route name (e.g. Route A - Main Town)" value={routeForm.name} onChange={e => setRouteForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Description (optional)" value={routeForm.description} onChange={e => setRouteForm(f => ({ ...f, description: e.target.value }))} />
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={routeForm.busId} onChange={e => setRouteForm(f => ({ ...f, busId: e.target.value }))}>
                <option value="">Assign Bus (optional)</option>
                {buses.map(b => <option key={b.id} value={b.id}>{b.plateNumber} — {b.model}</option>)}
              </select>
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={routeForm.driverId} onChange={e => setRouteForm(f => ({ ...f, driverId: e.target.value }))}>
                <option value="">Assign Driver (optional)</option>
                {drivers.map(d => <option key={d.id} value={d.id}>{d.name || d.staff?.user?.firstName}</option>)}
              </select>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button onClick={createRoute} disabled={saving}>{saving ? 'Creating...' : 'Create Route'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Pickup Point Modal */}
      {showPickupForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-bold mb-4">Add Pickup Stop</h2>
            <div className="space-y-3">
              <Input placeholder="Stop name (e.g. Main Junction)" value={pickupForm.name} onChange={e => setPickupForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Pickup time (e.g. 07:15)" value={pickupForm.time} onChange={e => setPickupForm(f => ({ ...f, time: e.target.value }))} />
              <Input placeholder="Landmark (optional)" value={pickupForm.landmark} onChange={e => setPickupForm(f => ({ ...f, landmark: e.target.value }))} />
              <Input type="number" placeholder="Sequence order" value={pickupForm.sequence} onChange={e => setPickupForm(f => ({ ...f, sequence: +e.target.value }))} />
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowPickupForm(false)}>Cancel</Button>
              <Button onClick={addPickup} disabled={saving}>{saving ? 'Adding...' : 'Add Stop'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
