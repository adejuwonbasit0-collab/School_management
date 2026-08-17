'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function HostelRoomsPage() {
  const [hostels, setHostels] = useState<any[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [selectedHostel, setSelectedHostel] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'rooms' | 'allocations' | 'add-room'>('rooms');
  const [saving, setSaving] = useState(false);
  const [roomForm, setRoomForm] = useState({ name: '', capacity: 4, floor: '', hostelId: '' });
  const [allocForm, setAllocForm] = useState({ studentId: '', hostelId: '', roomId: '', bedNumber: '', startDate: new Date().toISOString().split('T')[0] });

  useEffect(() => {
    Promise.all([
      apiClient.get('/hostel').catch(() => ({ data: [] })),
      apiClient.get('/hostel/allocations').catch(() => ({ data: [] })),
    ]).then(([h, a]) => {
      const hostelList = h.data?.data || h.data || [];
      setHostels(hostelList);
      setAllocations(a.data?.data || a.data || []);
      if (hostelList.length > 0) setSelectedHostel(hostelList[0].id);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedHostel) {
      apiClient.get(`/hostel/${selectedHostel}/rooms`).then(r => setRooms(r.data?.data || [])).catch(console.error);
    }
  }, [selectedHostel]);

  const createRoom = async () => {
    if (!roomForm.name || !selectedHostel) return alert('Room name required');
    setSaving(true);
    try {
      await apiClient.post(`/hostel/${selectedHostel}/rooms`, { ...roomForm, hostelId: selectedHostel });
      setRoomForm({ name: '', capacity: 4, floor: '', hostelId: '' });
      const res = await apiClient.get(`/hostel/${selectedHostel}/rooms`);
      setRooms(res.data?.data || []);
      setTab('rooms');
    } catch (e) { alert('Failed to create room'); }
    finally { setSaving(false); }
  };

  const allocateStudent = async () => {
    if (!allocForm.studentId || !allocForm.hostelId) return alert('Student and hostel required');
    setSaving(true);
    try {
      await apiClient.post('/hostel/allocations', allocForm);
      setAllocForm({ studentId: '', hostelId: '', roomId: '', bedNumber: '', startDate: new Date().toISOString().split('T')[0] });
      const res = await apiClient.get('/hostel/allocations');
      setAllocations(res.data?.data || res.data || []);
    } catch (e: any) { alert(e?.response?.data?.message || 'Allocation failed'); }
    finally { setSaving(false); }
  };

  const vacateStudent = async (id: string) => {
    if (!confirm('Vacate this student from hostel?')) return;
    await apiClient.put(`/hostel/allocations/${id}/vacate`);
    const res = await apiClient.get('/hostel/allocations');
    setAllocations(res.data?.data || res.data || []);
  };

  const occupancyRate = rooms.length > 0
    ? Math.round((rooms.reduce((acc, r) => acc + (r.allocations?.filter((a: any) => a.status === 'ACTIVE').length || 0), 0) /
        rooms.reduce((acc, r) => acc + r.capacity, 0)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hostel Management</h1>
          <p className="text-sm text-gray-500">Rooms, bed spaces, and student allocations</p>
        </div>
      </div>

      {/* Hostel selector */}
      {hostels.length > 0 && (
        <div className="flex gap-3 items-center flex-wrap">
          <label className="text-sm font-medium">Hostel:</label>
          <div className="flex gap-2 flex-wrap">
            {hostels.map(h => (
              <button key={h.id} onClick={() => setSelectedHostel(h.id)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${selectedHostel === h.id ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 hover:border-blue-300'}`}>
                {h.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4"><p className="text-sm text-gray-500">Hostels</p><p className="text-3xl font-bold text-blue-600">{hostels.length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Rooms</p><p className="text-3xl font-bold text-green-600">{rooms.length}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Total Capacity</p><p className="text-3xl font-bold text-purple-600">{rooms.reduce((a, r) => a + r.capacity, 0)}</p></Card>
        <Card className="p-4"><p className="text-sm text-gray-500">Occupancy</p><p className={`text-3xl font-bold ${occupancyRate > 90 ? 'text-red-600' : 'text-teal-600'}`}>{occupancyRate}%</p></Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'rooms' as const, label: '🏠 Rooms' },
          { key: 'allocations' as const, label: '👤 Allocations' },
          { key: 'add-room' as const, label: '+ Add Room' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Rooms grid */}
      {tab === 'rooms' && (
        !loading && rooms.length === 0 ? (
          <Card className="p-12 text-center text-gray-400">
            <div className="text-4xl mb-3">🏠</div>
            <p>No rooms created yet</p>
            <Button className="mt-4" onClick={() => setTab('add-room')}>Add first room</Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rooms.map(room => {
              const activeAllocs = (room.allocations || []).filter((a: any) => a.status === 'ACTIVE').length;
              const pct = Math.round((activeAllocs / room.capacity) * 100);
              return (
                <Card key={room.id} className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-semibold">{room.name}</h3>
                      {room.floor && <p className="text-xs text-gray-400">Floor {room.floor}</p>}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${pct >= 100 ? 'bg-red-100 text-red-700' : pct >= 75 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                      {pct >= 100 ? 'Full' : `${room.capacity - activeAllocs} free`}
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                    <div className={`h-2 rounded-full ${pct >= 100 ? 'bg-red-500' : pct >= 75 ? 'bg-yellow-500' : 'bg-green-500'}`}
                      style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                  <p className="text-xs text-gray-500">{activeAllocs} / {room.capacity} beds occupied</p>
                </Card>
              );
            })}
          </div>
        )
      )}

      {/* Allocations table */}
      {tab === 'allocations' && (
        <div className="space-y-4">
          {/* Quick allocate form */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Allocate Student</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Input placeholder="Student ID *" value={allocForm.studentId} onChange={e => setAllocForm(f => ({ ...f, studentId: e.target.value }))} />
              <select className="border rounded-lg px-3 py-2 text-sm" value={allocForm.hostelId} onChange={e => setAllocForm(f => ({ ...f, hostelId: e.target.value }))}>
                <option value="">Select Hostel *</option>
                {hostels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
              </select>
              <select className="border rounded-lg px-3 py-2 text-sm" value={allocForm.roomId} onChange={e => setAllocForm(f => ({ ...f, roomId: e.target.value }))}>
                <option value="">Select Room</option>
                {rooms.map(r => <option key={r.id} value={r.id}>{r.name} ({r.capacity - (r.allocations?.filter((a:any) => a.status === 'ACTIVE').length || 0)} free)</option>)}
              </select>
              <Button onClick={allocateStudent} disabled={saving}>{saving ? 'Allocating...' : 'Allocate'}</Button>
            </div>
          </Card>

          <Card>
            {allocations.length === 0 ? (
              <div className="p-12 text-center text-gray-400"><div className="text-4xl mb-3">👤</div><p>No allocations yet</p></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b"><tr>
                    <th className="px-4 py-3 text-left">Student</th>
                    <th className="px-4 py-3 text-left">Hostel</th>
                    <th className="px-4 py-3 text-left">Room</th>
                    <th className="px-4 py-3 text-left">Start Date</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr></thead>
                  <tbody>
                    {allocations.map(a => (
                      <tr key={a.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{a.student?.user?.firstName} {a.student?.user?.lastName}</td>
                        <td className="px-4 py-3 text-gray-600">{a.hostel?.name || '—'}</td>
                        <td className="px-4 py-3 text-gray-600">{a.room?.name || '—'}{a.bedNumber ? ` · Bed ${a.bedNumber}` : ''}</td>
                        <td className="px-4 py-3 text-gray-500">{new Date(a.startDate).toLocaleDateString()}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${a.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{a.status}</span>
                        </td>
                        <td className="px-4 py-3">
                          {a.status === 'ACTIVE' && <Button size="sm" variant="outline" onClick={() => vacateStudent(a.id)} className="text-red-600">Vacate</Button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Add Room form */}
      {tab === 'add-room' && (
        <Card className="p-6 max-w-md">
          <h2 className="font-semibold mb-4">Add New Room</h2>
          <div className="space-y-3">
            <div><label className="text-sm font-medium">Room Name *</label><Input className="mt-1" placeholder="e.g. Room 101A" value={roomForm.name} onChange={e => setRoomForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div><label className="text-sm font-medium">Capacity (beds)</label><Input className="mt-1" type="number" min={1} max={20} value={roomForm.capacity} onChange={e => setRoomForm(f => ({ ...f, capacity: +e.target.value }))} /></div>
            <div><label className="text-sm font-medium">Floor</label><Input className="mt-1" placeholder="e.g. Ground, 1st" value={roomForm.floor} onChange={e => setRoomForm(f => ({ ...f, floor: e.target.value }))} /></div>
          </div>
          <div className="flex gap-3 mt-5">
            <Button variant="outline" onClick={() => setTab('rooms')}>Cancel</Button>
            <Button onClick={createRoom} disabled={saving}>{saving ? 'Creating...' : 'Create Room'}</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
