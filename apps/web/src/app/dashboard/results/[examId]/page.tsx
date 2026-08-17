'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';

interface Subject { id: string; name: string; code?: string }
interface Student { id: string; admissionNo: string; name: string; rollNumber?: string }
interface BroadsheetRow extends Student {
  studentId?: string;
  subjects: { totalScore: number | string; grade: string }[];
  totalScore: number;
  percentage: number;
  grade: string;
  position: number | string;
}

export default function ResultDetailPage() {
  const { examId } = useParams<{ examId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const view = searchParams.get('view') || 'entry';

  const [exam, setExam] = useState<any>(null);
  const [classes, setClasses] = useState<any[]>([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [scores, setScores] = useState<Record<string, Record<string, any>>>({});
  const [broadsheet, setBroadsheet] = useState<{ subjects: Subject[]; rows: BroadsheetRow[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [publishing, setPublishing] = useState(false);
  const saveTimeout = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  useEffect(() => {
    loadExam();
    loadClasses();
  }, [examId]);

  useEffect(() => {
    if (selectedClass) {
      loadClassData();
      if (view === 'broadsheet') loadBroadsheet();
    }
  }, [selectedClass, view]);

  const loadExam = async () => {
    try {
      const res = await apiClient.get(`/examinations/${examId}`);
      setExam(res.data);
    } catch (e) { console.error(e); }
  };

  const loadClasses = async () => {
    try {
      const res = await apiClient.get('/classes');
      const list = res.data?.data?.data || [];
      setClasses(list);
      if (list.length > 0) setSelectedClass(list[0].id);
    } catch (e) { console.error(e); }
  };

  const loadClassData = async () => {
    setLoading(true);
    try {
      const [classRes, resultsRes] = await Promise.all([
        apiClient.get(`/classes/${selectedClass}`),
        apiClient.get(`/results/examinations/${examId}/results`),
      ]);

      const cls = classRes.data?.data || {};
      const subjectList: Subject[] = (cls.subjects || []).map((cs: any) => cs.subject);
      const studentList: Student[] = (cls.enrollments || []).map((e: any) => ({
        id: e.student?.id || e.id,
        admissionNo: e.student?.admissionNo || e.admissionNo,
        name: e.student?.user ? `${e.student.user.firstName} ${e.student.user.lastName}` : e.name,
        rollNumber: e.rollNumber,
      }));

      setSubjects(subjectList);
      setStudents(studentList);

      // Pre-fill existing scores
      const existingScores: Record<string, Record<string, any>> = {};
      for (const result of (resultsRes.data?.data || [])) {
        existingScores[result.studentId] = result.scores || {};
      }
      setScores(existingScores);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadBroadsheet = async () => {
    try {
      const res = await apiClient.get(`/results/examinations/${examId}/broadsheet?classRoomId=${selectedClass}`);
      setBroadsheet(res.data);
    } catch (e) { console.error(e); }
  };

  const handleScoreChange = (studentId: string, subjectId: string, field: string, value: string) => {
    setScores(prev => ({
      ...prev,
      [studentId]: {
        ...(prev[studentId] || {}),
        [subjectId]: {
          ...(prev[studentId]?.[subjectId] || {}),
          [field]: value === '' ? '' : parseFloat(value) || 0,
        },
      },
    }));

    // Auto-save debounce
    const key = `${studentId}-${subjectId}`;
    clearTimeout(saveTimeout.current[key]);
    saveTimeout.current[key] = setTimeout(() => saveStudentScores(studentId), 1200);
  };

  const saveStudentScores = async (studentId: string) => {
    const studentScores = scores[studentId];
    if (!studentScores) return;

    setSaving(prev => ({ ...prev, [studentId]: true }));
    try {
      await apiClient.post(`/results/examinations/${examId}/results/${studentId}`, {
        scores: studentScores,
      });
    } catch (e) {
      console.error('Auto-save failed', e);
    } finally {
      setSaving(prev => ({ ...prev, [studentId]: false }));
    }
  };

  const saveAll = async () => {
    for (const student of students) {
      await saveStudentScores(student.id);
    }
  };

  const computePositions = async () => {
    await saveAll();
    try {
      await apiClient.post(`/results/examinations/${examId}/compute-positions`);
      alert('Positions computed successfully!');
      if (view === 'broadsheet') loadBroadsheet();
    } catch (e) { alert('Failed to compute positions'); }
  };

  const publishResults = async () => {
    if (!confirm('Publish results? Students and parents will be notified.')) return;
    setPublishing(true);
    try {
      await apiClient.post(`/results/examinations/${examId}/publish`);
      alert('Results published!');
      loadExam();
    } catch (e) {
      alert('Failed to publish');
    } finally {
      setPublishing(false);
    }
  };

  const downloadReportCard = (studentId: string) => {
    const url = `${process.env.NEXT_PUBLIC_API_URL}/results/examinations/${examId}/students/${studentId}/report-card`;
    window.open(url, '_blank');
  };

  const downloadBroadsheetPDF = () => {
    alert('PDF export — integrate with your PDF endpoint here');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-1 block">
            ← Back to Results
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{exam?.name || 'Loading...'}</h1>
          <p className="text-sm text-gray-500">{exam?.term?.name} · {exam?.academicYear?.name}</p>
        </div>
        <div className="flex gap-2">
          {view === 'entry' && (
            <>
              <Button variant="outline" onClick={computePositions}>Compute Positions</Button>
              <Button onClick={publishResults} disabled={publishing}>
                {publishing ? 'Publishing...' : 'Publish Results'}
              </Button>
            </>
          )}
          {view === 'broadsheet' && (
            <Button variant="outline" onClick={downloadBroadsheetPDF}>⬇ PDF</Button>
          )}
        </div>
      </div>

      {/* View Toggle + Class Select */}
      <div className="flex items-center gap-4">
        <div className="flex rounded-lg border overflow-hidden">
          <button
            onClick={() => router.push(`/dashboard/results/${examId}`)}
            className={`px-4 py-2 text-sm font-medium ${view !== 'broadsheet' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Score Entry
          </button>
          <button
            onClick={() => router.push(`/dashboard/results/${examId}?view=broadsheet`)}
            className={`px-4 py-2 text-sm font-medium ${view === 'broadsheet' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Broadsheet
          </button>
        </div>

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

      {/* Score Entry Grid */}
      {view !== 'broadsheet' && (
        <Card>
          {loading ? (
            <div className="p-12 text-center text-gray-400">Loading class data...</div>
          ) : !selectedClass ? (
            <div className="p-12 text-center text-gray-400">Select a class to enter scores</div>
          ) : subjects.length === 0 ? (
            <div className="p-12 text-center text-gray-400">No subjects assigned to this class</div>
          ) : (
            <>
              <div className="p-4 flex items-center justify-between border-b">
                <p className="text-sm text-gray-600">{students.length} students · {subjects.length} subjects</p>
                <Button size="sm" onClick={saveAll}>💾 Save All</Button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 border-b sticky top-0">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-600 w-8">#</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600 min-w-[160px]">Student</th>
                      {subjects.map(sub => (
                        <th key={sub.id} className="px-2 py-2 text-center font-medium text-gray-600 min-w-[160px]" colSpan={2}>
                          <div>{sub.name}</div>
                          <div className="flex text-gray-400 gap-1 justify-center font-normal">
                            <span className="w-16 text-center">CA</span>
                            <span className="w-16 text-center">Exam</span>
                          </div>
                        </th>
                      ))}
                      <th className="px-3 py-2 text-center font-medium text-gray-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student, idx) => (
                      <tr key={student.id} className="border-b hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-400">{idx + 1}</td>
                        <td className="px-3 py-2">
                          <div className="font-medium text-gray-900">{student.name}</div>
                          <div className="text-gray-400">{student.admissionNo}</div>
                          {saving[student.id] && <div className="text-blue-400">saving...</div>}
                        </td>
                        {subjects.map(sub => (
                          <>
                            <td key={`${student.id}-${sub.id}-ca`} className="px-1 py-2">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                className="w-16 border rounded px-2 py-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                value={scores[student.id]?.[sub.id]?.caScore ?? ''}
                                onChange={e => handleScoreChange(student.id, sub.id, 'caScore', e.target.value)}
                                placeholder="CA"
                              />
                            </td>
                            <td key={`${student.id}-${sub.id}-ex`} className="px-1 py-2">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                className="w-16 border rounded px-2 py-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                value={scores[student.id]?.[sub.id]?.examScore ?? ''}
                                onChange={e => handleScoreChange(student.id, sub.id, 'examScore', e.target.value)}
                                placeholder="Exam"
                              />
                            </td>
                          </>
                        ))}
                        <td className="px-3 py-2 text-center">
                          <button
                            onClick={() => downloadReportCard(student.id)}
                            className="text-xs text-blue-600 hover:underline"
                            title="Download Report Card"
                          >
                            📄 Card
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>
      )}

      {/* Broadsheet View */}
      {view === 'broadsheet' && (
        <Card>
          {!broadsheet ? (
            <div className="p-12 text-center text-gray-400">Loading broadsheet...</div>
          ) : (
            <>
              <div className="p-4 border-b">
                <h2 className="font-semibold text-gray-900">Class Broadsheet</h2>
                <p className="text-sm text-gray-500">{broadsheet.rows.length} students</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-3 py-2 text-left">Pos</th>
                      <th className="px-3 py-2 text-left">Student</th>
                      <th className="px-3 py-2 text-left">Adm No</th>
                      {broadsheet.subjects.map(s => (
                        <th key={s.id} className="px-2 py-2 text-center min-w-[80px]">
                          <div>{s.code || s.name.slice(0, 5)}</div>
                        </th>
                      ))}
                      <th className="px-3 py-2 text-center">Total</th>
                      <th className="px-3 py-2 text-center">%</th>
                      <th className="px-3 py-2 text-center">Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {broadsheet.rows.map((row, idx) => (
                      <tr key={row.studentId} className={`border-b ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                        <td className="px-3 py-2 text-center font-semibold text-blue-600">{row.position}</td>
                        <td className="px-3 py-2 font-medium">{row.name}</td>
                        <td className="px-3 py-2 text-gray-500">{row.admissionNo}</td>
                        {row.subjects.map((s, si) => (
                          <td key={si} className="px-2 py-2 text-center">
                            <div>{s.totalScore}</div>
                            <div className="text-gray-400">{s.grade}</div>
                          </td>
                        ))}
                        <td className="px-3 py-2 text-center font-semibold">{Number(row.totalScore).toFixed(1)}</td>
                        <td className="px-3 py-2 text-center">{Number(row.percentage).toFixed(1)}%</td>
                        <td className="px-3 py-2 text-center">
                          <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-medium">
                            {row.grade}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
