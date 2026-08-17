'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'all-courses' | 'my-courses' | 'create';

const MATERIAL_TYPES = [
  { value: 'VIDEO', label: '🎥 Video', icon: '🎥' },
  { value: 'PDF', label: '📄 PDF/Document', icon: '📄' },
  { value: 'NOTE', label: '📝 Note/Text', icon: '📝' },
  { value: 'LINK', label: '🔗 External Link', icon: '🔗' },
  { value: 'ASSIGNMENT', label: '📋 Assignment', icon: '📋' },
  { value: 'QUIZ', label: '🧪 Quiz', icon: '🧪' },
];

export default function LmsPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('all-courses');
  const [courses, setCourses] = useState<any[]>([]);
  const [myCourses, setMyCourses] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedCourse, setSelectedCourse] = useState<any>(null);
  const [showMaterialForm, setShowMaterialForm] = useState(false);
  const [materialForm, setMaterialForm] = useState({ title: '', type: 'VIDEO', url: '', content: '', duration: 0 });
  const [saving, setSaving] = useState(false);

  // Create course form
  const [createForm, setCreateForm] = useState({ title: '', description: '', objectives: [''], duration: '' });

  useEffect(() => {
    apiClient.get('/lms/stats').then(r => setStats(r.data?.data)).catch(console.error);
    loadTab(tab);
  }, []);

  useEffect(() => { loadTab(tab); }, [tab]);

  const loadTab = async (t: Tab) => {
    setLoading(true);
    try {
      if (t === 'all-courses') {
        const res = await apiClient.get('/lms/courses');
        setCourses(res.data?.data?.data || []);
      } else if (t === 'my-courses') {
        const res = await apiClient.get('/lms/my-courses');
        setMyCourses(res.data?.data || []);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const createCourse = async () => {
    if (!createForm.title.trim()) return alert('Title required');
    setSaving(true);
    try {
      await apiClient.post('/lms/courses', {
        ...createForm,
        objectives: createForm.objectives.filter(Boolean),
      });
      setCreateForm({ title: '', description: '', objectives: [''], duration: '' });
      setTab('all-courses');
    } catch (e) { alert('Failed to create course'); }
    finally { setSaving(false); }
  };

  const publishCourse = async (id: string) => {
    try {
      await apiClient.patch(`/lms/courses/${id}/publish`);
      loadTab('all-courses');
    } catch (e) { alert('Failed to publish'); }
  };

  const deleteCourse = async (id: string) => {
    if (!confirm('Delete this course?')) return;
    try {
      await apiClient.delete(`/lms/courses/${id}`);
      loadTab('all-courses');
      if (selectedCourse?.id === id) setSelectedCourse(null);
    } catch (e) { alert('Delete failed'); }
  };

  const addMaterial = async () => {
    if (!selectedCourse || !materialForm.title) return;
    setSaving(true);
    try {
      await apiClient.post(`/lms/courses/${selectedCourse.id}/materials`, materialForm);
      const res = await apiClient.get(`/lms/courses/${selectedCourse.id}`);
      setSelectedCourse(res.data);
      setShowMaterialForm(false);
      setMaterialForm({ title: '', type: 'VIDEO', url: '', content: '', duration: 0 });
    } catch (e) { alert('Failed to add material'); }
    finally { setSaving(false); }
  };

  const removeMaterial = async (materialId: string) => {
    if (!confirm('Remove this material?')) return;
    await apiClient.delete(`/lms/courses/${selectedCourse.id}/materials/${materialId}`);
    const res = await apiClient.get(`/lms/courses/${selectedCourse.id}`);
    setSelectedCourse(res.data);
  };

  const enrollStudent = async (courseId: string) => {
    const studentId = prompt('Enter student ID to enroll:');
    if (!studentId) return;
    try {
      await apiClient.post(`/lms/courses/${courseId}/enroll`, { studentId });
      alert('Student enrolled!');
    } catch (e) { alert('Enrollment failed'); }
  };

  const filtered = courses.filter(c => !search || c.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Learning Management System</h1>
          <p className="text-sm text-gray-500">Create and manage courses, materials, assignments, and quizzes</p>
        </div>
        <Button onClick={() => setTab('create')}>+ Create Course</Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Total Courses</p><p className="text-3xl font-bold text-blue-600">{stats.totalCourses}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Published</p><p className="text-3xl font-bold text-green-600">{stats.publishedCourses}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Total Enrollments</p><p className="text-3xl font-bold text-purple-600">{stats.totalEnrollments}</p></Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'all-courses' as Tab, label: '📚 All Courses' },
          { key: 'my-courses' as Tab, label: '🎓 My Enrolled Courses' },
          { key: 'create' as Tab, label: '✏️ Create Course' },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Create Course Tab */}
      {tab === 'create' && (
        <Card className="p-6 max-w-2xl">
          <h2 className="font-semibold text-lg mb-5">New Course</h2>
          <div className="space-y-4">
            <div><label className="text-sm font-medium">Course Title *</label>
              <Input className="mt-1" placeholder="e.g. Introduction to Algebra" value={createForm.title} onChange={e => setCreateForm(f => ({ ...f, title: e.target.value }))} />
            </div>
            <div><label className="text-sm font-medium">Description</label>
              <textarea className="w-full mt-1 border rounded-lg px-3 py-2 text-sm resize-none" rows={3} placeholder="What will students learn?" value={createForm.description} onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div><label className="text-sm font-medium">Duration</label>
              <Input className="mt-1" placeholder="e.g. 8 weeks, 24 hours" value={createForm.duration} onChange={e => setCreateForm(f => ({ ...f, duration: e.target.value }))} />
            </div>
            <div>
              <label className="text-sm font-medium">Learning Objectives</label>
              {createForm.objectives.map((obj, i) => (
                <div key={i} className="flex gap-2 mt-1">
                  <Input placeholder={`Objective ${i + 1}`} value={obj} onChange={e => {
                    const updated = [...createForm.objectives];
                    updated[i] = e.target.value;
                    setCreateForm(f => ({ ...f, objectives: updated }));
                  }} />
                  {i > 0 && <button onClick={() => setCreateForm(f => ({ ...f, objectives: f.objectives.filter((_, idx) => idx !== i) }))} className="text-red-400 hover:text-red-600">✕</button>}
                </div>
              ))}
              <button onClick={() => setCreateForm(f => ({ ...f, objectives: [...f.objectives, ''] }))} className="text-blue-600 text-sm mt-2 hover:underline">+ Add objective</button>
            </div>
            <Button onClick={createCourse} disabled={saving} className="w-full">{saving ? 'Creating...' : 'Create Course'}</Button>
          </div>
        </Card>
      )}

      {/* All Courses Tab */}
      {tab === 'all-courses' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Course list */}
          <div className="space-y-3">
            <Input placeholder="Search courses..." value={search} onChange={e => setSearch(e.target.value)} />
            {loading ? <div className="text-center text-gray-400 py-12">Loading...</div> :
              filtered.length === 0 ? (
                <Card className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-3">📚</div>
                  <p>No courses yet</p>
                  <Button className="mt-4" onClick={() => setTab('create')}>Create first course</Button>
                </Card>
              ) : filtered.map(course => {
                const meta = course.meta || course.content || {};
                const enrolled = (meta.enrolledStudents || []).length;
                const materials = (meta.modules || []).length;
                return (
                  <Card key={course.id}
                    className={`p-4 cursor-pointer hover:border-blue-300 transition-colors ${selectedCourse?.id === course.id ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedCourse(course)}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-900">{course.title}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${course.isPublished ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                            {course.isPublished ? 'Published' : 'Draft'}
                          </span>
                        </div>
                        {meta.description && <p className="text-sm text-gray-500 line-clamp-2">{meta.description}</p>}
                        <div className="flex gap-4 mt-2 text-xs text-gray-400">
                          <span>📦 {materials} materials</span>
                          <span>👥 {enrolled} enrolled</span>
                          {meta.duration && <span>⏱ {meta.duration}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3" onClick={e => e.stopPropagation()}>
                      {!course.isPublished && <Button size="sm" onClick={() => publishCourse(course.id)}>📢 Publish</Button>}
                      <Button size="sm" variant="outline" onClick={() => enrollStudent(course.id)}>+ Enroll Student</Button>
                      <Button size="sm" variant="outline" onClick={() => deleteCourse(course.id)} className="text-red-600">Delete</Button>
                    </div>
                  </Card>
                );
              })}
          </div>

          {/* Course detail panel */}
          {selectedCourse ? (
            <Card className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-lg">{selectedCourse.title}</h2>
                <Button size="sm" onClick={() => setShowMaterialForm(true)}>+ Add Material</Button>
              </div>

              {/* Materials list */}
              {(selectedCourse.meta?.modules || selectedCourse.content?.modules || []).length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  <div className="text-3xl mb-2">📦</div>
                  <p className="text-sm">No materials yet</p>
                  <button onClick={() => setShowMaterialForm(true)} className="text-blue-600 text-sm hover:underline mt-1">Add first material</button>
                </div>
              ) : (
                <div className="space-y-2">
                  {(selectedCourse.meta?.modules || selectedCourse.content?.modules || []).map((mod: any, i: number) => {
                    const typeInfo = MATERIAL_TYPES.find(t => t.value === mod.type);
                    return (
                      <div key={mod.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg group">
                        <span className="text-xl">{typeInfo?.icon || '📎'}</span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm">{mod.title}</p>
                          <p className="text-xs text-gray-400">{mod.type}{mod.duration ? ` · ${mod.duration} min` : ''}</p>
                        </div>
                        <span className="text-xs text-gray-400">#{i + 1}</span>
                        <button onClick={() => removeMaterial(mod.id)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs transition-opacity">Remove</button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Objectives */}
              {(selectedCourse.meta?.objectives || selectedCourse.content?.objectives || []).length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="font-medium text-sm mb-2">Learning Objectives</p>
                  <ul className="space-y-1">
                    {(selectedCourse.meta?.objectives || selectedCourse.content?.objectives || []).map((obj: string, i: number) => (
                      <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>{obj}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          ) : (
            <div className="hidden lg:flex items-center justify-center text-gray-300 h-64">
              <div className="text-center"><div className="text-5xl mb-3">📚</div><p>Select a course to view details</p></div>
            </div>
          )}
        </div>
      )}

      {/* My Enrolled Courses */}
      {tab === 'my-courses' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? <div className="col-span-3 text-center text-gray-400 py-12">Loading...</div> :
            myCourses.length === 0 ? (
              <Card className="col-span-3 p-12 text-center text-gray-400">
                <div className="text-4xl mb-3">🎓</div>
                <p>Not enrolled in any courses yet</p>
              </Card>
            ) : myCourses.map(course => {
              const meta = course.content || {};
              return (
                <Card key={course.id} className="p-5 hover:shadow-md transition-shadow">
                  <div className="w-full h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg mb-4 flex items-center justify-center text-white text-3xl">
                    📚
                  </div>
                  <h3 className="font-semibold">{course.title}</h3>
                  {meta.description && <p className="text-sm text-gray-500 mt-1 line-clamp-2">{meta.description}</p>}
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-xs text-gray-400">{(meta.modules || []).length} materials</span>
                    <Button size="sm" onClick={() => setSelectedCourse(course)}>Continue →</Button>
                  </div>
                </Card>
              );
            })}
        </div>
      )}

      {/* Add Material Modal */}
      {showMaterialForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Add Course Material</h2>
            <div className="space-y-3">
              <div><label className="text-sm font-medium">Type</label>
                <select className="w-full mt-1 border rounded-lg px-3 py-2 text-sm" value={materialForm.type} onChange={e => setMaterialForm(f => ({ ...f, type: e.target.value }))}>
                  {MATERIAL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <Input placeholder="Material title *" value={materialForm.title} onChange={e => setMaterialForm(f => ({ ...f, title: e.target.value }))} />
              {['VIDEO', 'PDF', 'LINK'].includes(materialForm.type) && (
                <Input placeholder="URL (video/file/link)" value={materialForm.url} onChange={e => setMaterialForm(f => ({ ...f, url: e.target.value }))} />
              )}
              {['NOTE', 'ASSIGNMENT'].includes(materialForm.type) && (
                <textarea className="w-full border rounded-lg px-3 py-2 text-sm resize-none" rows={4} placeholder="Content / Instructions" value={materialForm.content} onChange={e => setMaterialForm(f => ({ ...f, content: e.target.value }))} />
              )}
              {materialForm.type === 'VIDEO' && (
                <Input type="number" placeholder="Duration (minutes)" value={materialForm.duration || ''} onChange={e => setMaterialForm(f => ({ ...f, duration: +e.target.value }))} />
              )}
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowMaterialForm(false)}>Cancel</Button>
              <Button onClick={addMaterial} disabled={saving}>{saving ? 'Adding...' : 'Add Material'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
