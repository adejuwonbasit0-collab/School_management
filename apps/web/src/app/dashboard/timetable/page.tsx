'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const TIME_SLOTS = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'];

interface Slot {
  id: string;
  dayOfWeek: number;
  startTime: string;
  endTime: string;
  subject: { id: string; name: string; code?: string };
  room?: string;
}

interface SlotForm {
  subjectId: string;
  teacherId: string;
  startTime: string;
  endTime: string;
  room: string;
}

export default function TimetablePage() {
  const [classes, setClasses] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [teachers, setTeachers] = useState<any[]>([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [timetable, setTimetable] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectedTime, setSelectedTime] = useState('');
  const [editSlot, setEditSlot] = useState<Slot | null>(null);
  const [form, setForm] = useState<SlotForm>({ subjectId: '', teacherId: '', startTime: '', endTime: '', room: '' });
  const [saving, setSaving] = useState(false);
  const [conflictError, setConflictError] = useState('');

  useEffect(() => {
    loadInitial();
  }, []);

  useEffect(() => {
    if (selectedClass) loadTimetable();
  }, [selectedClass]);

  const loadInitial = async () => {
    try {
      const [classRes, subRes, teachRes] = await Promise.all([
        apiClient.get('/timetable/classes'),
        apiClient.get('/subjects'),
        apiClient.get('/teachers'),
      ]);
      const classList = classRes.data?.data || [];
      setClasses(classList);
      setSubjects(subRes.data?.data?.data || []);
      setTeachers(teachRes.data?.data?.data || []);
      if (classList.length > 0) setSelectedClass(classList[0].id);
    } catch (e) { console.error(e); }
  };

  const loadTimetable = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/timetable/class/${selectedClass}`);
      setTimetable(res.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const openAddSlot = (day: number, time: string) => {
    setEditSlot(null);
    setSelectedDay(day);
    const endTime = TIME_SLOTS[TIME_SLOTS.indexOf(time) + 1] || `${parseInt(time) + 1}:00`;
    setForm({ subjectId: '', teacherId: '', startTime: time, endTime, room: '' });
    setConflictError('');
    setShowModal(true);
  };

  const openEditSlot = (slot: Slot) => {
    setEditSlot(slot);
    setSelectedDay(slot.dayOfWeek);
    setForm({
      subjectId: slot.subject.id,
      teacherId: '',
      startTime: slot.startTime,
      endTime: slot.endTime,
      room: slot.room || '',
    });
    setConflictError('');
    setShowModal(true);
  };

  const saveSlot = async () => {
    if (!form.subjectId || !form.startTime || !form.endTime) {
      return alert('Please fill subject and times');
    }
    setSaving(true);
    setConflictError('');
    try {
      if (editSlot) {
        await apiClient.put(`/timetable/slots/${editSlot.id}`, {
          subjectId: form.subjectId,
          teacherId: form.teacherId || undefined,
          dayOfWeek: selectedDay,
          startTime: form.startTime,
          endTime: form.endTime,
          room: form.room || undefined,
        });
      } else {
        await apiClient.post('/timetable/slots', {
          classRoomId: selectedClass,
          subjectId: form.subjectId,
          teacherId: form.teacherId || undefined,
          dayOfWeek: selectedDay,
          startTime: form.startTime,
          endTime: form.endTime,
          room: form.room || undefined,
        });
      }
      setShowModal(false);
      loadTimetable();
    } catch (err: any) {
      const msg = err?.response?.data?.message || 'Save failed';
      if (msg.toLowerCase().includes('conflict')) {
        setConflictError(msg);
      } else {
        alert(msg);
      }
    } finally {
      setSaving(false);
    }
  };

  const deleteSlot = async () => {
    if (!editSlot) return;
    if (!confirm('Remove this slot?')) return;
    try {
      await apiClient.delete(`/timetable/slots/${editSlot.id}`);
      setShowModal(false);
      loadTimetable();
    } catch (e) { alert('Delete failed'); }
  };

  const getSlot = (day: number, time: string): Slot | undefined =>
    timetable.find(s => s.dayOfWeek === day && s.startTime === time);

  const SUBJECT_COLORS = [
    'bg-blue-100 text-blue-800 border-blue-200',
    'bg-green-100 text-green-800 border-green-200',
    'bg-purple-100 text-purple-800 border-purple-200',
    'bg-yellow-100 text-yellow-800 border-yellow-200',
    'bg-pink-100 text-pink-800 border-pink-200',
    'bg-indigo-100 text-indigo-800 border-indigo-200',
    'bg-orange-100 text-orange-800 border-orange-200',
  ];

  const subjectColorMap: Record<string, string> = {};
  let colorIdx = 0;
  for (const slot of timetable) {
    if (!subjectColorMap[slot.subject.id]) {
      subjectColorMap[slot.subject.id] = SUBJECT_COLORS[colorIdx % SUBJECT_COLORS.length];
      colorIdx++;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Timetable Builder</h1>
          <p className="text-sm text-gray-500">Click a cell to add a lesson slot. Conflicts are detected automatically.</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border rounded-lg px-3 py-2 text-sm bg-white"
            value={selectedClass}
            onChange={e => setSelectedClass(e.target.value)}
          >
            <option value="">Select Class</option>
            {classes.map(c => (
              <option key={c.id} value={c.id}>{c.name}{c.section ? ` ${c.section}` : ''}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Legend */}
      {timetable.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(subjectColorMap).map(([subId, color]) => {
            const sub = timetable.find(s => s.subject.id === subId)?.subject;
            return sub ? (
              <span key={subId} className={`text-xs px-2 py-1 rounded border ${color}`}>
                {sub.name}
              </span>
            ) : null;
          })}
        </div>
      )}

      {/* Grid */}
      <Card className="overflow-x-auto">
        {loading ? (
          <div className="p-12 text-center text-gray-400">Loading timetable...</div>
        ) : !selectedClass ? (
          <div className="p-12 text-center text-gray-400">Select a class to view or build its timetable</div>
        ) : (
          <table className="w-full text-sm border-collapse min-w-[700px]">
            <thead>
              <tr>
                <th className="w-20 bg-gray-50 border px-3 py-3 text-left text-gray-600">Time</th>
                {DAYS.map(day => (
                  <th key={day} className="bg-gray-50 border px-3 py-3 text-center text-gray-700 font-semibold">
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TIME_SLOTS.slice(0, -1).map((time, ti) => (
                <tr key={time}>
                  <td className="border px-3 py-2 text-xs text-gray-500 bg-gray-50 whitespace-nowrap">
                    {time} – {TIME_SLOTS[ti + 1]}
                  </td>
                  {DAYS.map((_, di) => {
                    const day = di + 1;
                    const slot = getSlot(day, time);
                    return (
                      <td key={di} className="border p-1 h-16 align-top">
                        {slot ? (
                          <button
                            onClick={() => openEditSlot(slot)}
                            className={`w-full h-full rounded p-2 text-left text-xs border hover:opacity-90 transition-opacity ${subjectColorMap[slot.subject.id] || 'bg-gray-100 text-gray-700 border-gray-200'}`}
                          >
                            <div className="font-semibold">{slot.subject.name}</div>
                            {slot.room && <div className="text-xs opacity-70">🏫 {slot.room}</div>}
                          </button>
                        ) : (
                          <button
                            onClick={() => openAddSlot(day, time)}
                            className="w-full h-full rounded hover:bg-blue-50 hover:border-blue-200 border border-dashed border-transparent text-gray-300 hover:text-blue-400 transition-all text-lg"
                            title="Add lesson"
                          >
                            +
                          </button>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">
              {editSlot ? 'Edit Slot' : `Add Slot — ${DAYS[(selectedDay || 1) - 1]}, ${form.startTime}`}
            </h2>

            {conflictError && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
                ⚠️ {conflictError}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Subject *</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.subjectId}
                  onChange={e => setForm(f => ({ ...f, subjectId: e.target.value }))}
                >
                  <option value="">Select subject</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Teacher (optional)</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.teacherId}
                  onChange={e => setForm(f => ({ ...f, teacherId: e.target.value }))}
                >
                  <option value="">Select teacher</option>
                  {teachers.map((t: any) => (
                    <option key={t.id} value={t.id}>
                      {t.staff?.user?.firstName} {t.staff?.user?.lastName}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Start Time *</label>
                  <select
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={form.startTime}
                    onChange={e => setForm(f => ({ ...f, startTime: e.target.value }))}
                  >
                    {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Time *</label>
                  <select
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={form.endTime}
                    onChange={e => setForm(f => ({ ...f, endTime: e.target.value }))}
                  >
                    {TIME_SLOTS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Room (optional)</label>
                <Input
                  placeholder="e.g. Room 12A"
                  value={form.room}
                  onChange={e => setForm(f => ({ ...f, room: e.target.value }))}
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              {editSlot && (
                <Button variant="outline" onClick={deleteSlot} className="text-red-600 border-red-200 hover:bg-red-50">
                  Remove
                </Button>
              )}
              <div className="flex-1" />
              <Button variant="outline" onClick={() => setShowModal(false)}>Cancel</Button>
              <Button onClick={saveSlot} disabled={saving}>
                {saving ? 'Saving...' : editSlot ? 'Update' : 'Add Slot'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
