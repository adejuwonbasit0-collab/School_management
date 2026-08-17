'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const SEVERITY_COLORS: Record<string, string> = {
  INFO: 'bg-blue-100 text-blue-700',
  WARN: 'bg-yellow-100 text-yellow-700',
  ERROR: 'bg-red-100 text-red-700',
  CRITICAL: 'bg-red-200 text-red-900',
};

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState({ entity: '', action: '', severity: '', page: 1 });
  const [total, setTotal] = useState(0);

  useEffect(() => {
    apiClient.get('/audit/summary').then(r => setSummary(r.data?.data)).catch(console.error);
  }, []);

  useEffect(() => { loadLogs(); }, [query]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '50', page: String(query.page) });
      if (query.entity) params.set('entity', query.entity);
      if (query.action) params.set('action', query.action);
      if (query.severity) params.set('severity', query.severity);
      const res = await apiClient.get(`/audit/logs?${params}`);
      setLogs(res.data?.data?.data || []);
      setTotal(res.data?.data?.total || 0);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-sm text-gray-500">Complete activity trail and security monitoring</p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Today&apos;s Activity</p><p className="text-3xl font-bold text-blue-600">{summary.todayCount}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">This Week</p><p className="text-3xl font-bold text-green-600">{summary.weekCount}</p></Card>
          {(summary.bySeverity || []).slice(0, 2).map((s: any) => (
            <Card key={s.severity} className="p-4">
              <p className="text-sm text-gray-500">{s.severity}</p>
              <p className="text-3xl font-bold text-gray-900">{s._count}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Top Entities */}
      {summary?.byEntity && (
        <Card className="p-4">
          <p className="font-semibold mb-3">Most Active Entities</p>
          <div className="flex flex-wrap gap-2">
            {summary.byEntity.map((e: any) => (
              <button key={e.entity} onClick={() => setQuery(q => ({ ...q, entity: e.entity, page: 1 }))}
                className="text-xs bg-gray-100 hover:bg-blue-100 hover:text-blue-700 px-3 py-1.5 rounded-full transition-colors">
                {e.entity} <span className="font-semibold ml-1">{e._count}</span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <Input placeholder="Filter by entity..." value={query.entity} onChange={e => setQuery(q => ({ ...q, entity: e.target.value, page: 1 }))} className="w-44" />
        <Input placeholder="Filter by action..." value={query.action} onChange={e => setQuery(q => ({ ...q, action: e.target.value, page: 1 }))} className="w-44" />
        <select className="border rounded-lg px-3 py-2 text-sm bg-white" value={query.severity} onChange={e => setQuery(q => ({ ...q, severity: e.target.value, page: 1 }))}>
          <option value="">All Severities</option>
          {['INFO', 'WARN', 'ERROR', 'CRITICAL'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {(query.entity || query.action || query.severity) && (
          <Button variant="outline" size="sm" onClick={() => setQuery({ entity: '', action: '', severity: '', page: 1 })}>Clear</Button>
        )}
      </div>

      <Card>
        <div className="p-4 border-b flex items-center justify-between">
          <span className="text-sm text-gray-500">{total.toLocaleString()} records</span>
        </div>
        {loading ? <div className="p-12 text-center text-gray-400">Loading logs...</div> :
          logs.length === 0 ? <div className="p-12 text-center text-gray-400">No logs found</div> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 border-b"><tr>
                  <th className="px-4 py-3 text-left">Time</th><th className="px-4 py-3 text-left">Severity</th>
                  <th className="px-4 py-3 text-left">Entity</th><th className="px-4 py-3 text-left">Action</th>
                  <th className="px-4 py-3 text-left">User</th><th className="px-4 py-3 text-left">IP</th>
                </tr></thead>
                <tbody>{logs.map(log => (
                  <tr key={log.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500 whitespace-nowrap">{new Date(log.createdAt).toLocaleString()}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full font-medium text-xs ${SEVERITY_COLORS[log.severity] || 'bg-gray-100'}`}>{log.severity}</span>
                    </td>
                    <td className="px-4 py-2 font-medium text-gray-800">{log.entity}</td>
                    <td className="px-4 py-2 text-gray-600">{log.action}</td>
                    <td className="px-4 py-2 text-gray-500">{log.userId?.slice(0, 8) || '—'}</td>
                    <td className="px-4 py-2 text-gray-400">{log.ipAddress || '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        {/* Pagination */}
        {total > 50 && (
          <div className="p-4 border-t flex items-center justify-between text-sm">
            <span className="text-gray-500">Page {query.page} of {Math.ceil(total / 50)}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={query.page === 1} onClick={() => setQuery(q => ({ ...q, page: q.page - 1 }))}>← Prev</Button>
              <Button size="sm" variant="outline" disabled={query.page >= Math.ceil(total / 50)} onClick={() => setQuery(q => ({ ...q, page: q.page + 1 }))}>Next →</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
