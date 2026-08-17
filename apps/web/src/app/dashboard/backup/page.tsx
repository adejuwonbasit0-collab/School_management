'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: 'bg-green-100 text-green-700',
  RUNNING: 'bg-blue-100 text-blue-700',
  PENDING: 'bg-yellow-100 text-yellow-700',
  FAILED: 'bg-red-100 text-red-700',
};

const formatBytes = (bytes?: bigint | null) => {
  if (!bytes) return '—';
  const b = Number(bytes);
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`;
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

export default function BackupPage() {
  const [backups, setBackups] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const [s, b] = await Promise.all([
        apiClient.get('/backup/stats'),
        apiClient.get('/backup'),
      ]);
      setStats(s.data?.data);
      setBackups(b.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const triggerBackup = async (type: 'FULL' | 'INCREMENTAL') => {
    setTriggering(true);
    try {
      await apiClient.post('/backup/trigger', { type });
      setTimeout(load, 4000); // refresh after async backup completes
    } catch (e) { alert('Backup trigger failed'); }
    finally { setTriggering(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backup & Recovery</h1>
          <p className="text-sm text-gray-500">Manage database and file backups</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => triggerBackup('INCREMENTAL')} disabled={triggering}>
            📦 Incremental Backup
          </Button>
          <Button onClick={() => triggerBackup('FULL')} disabled={triggering}>
            {triggering ? 'Starting...' : '💾 Full Backup'}
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Total Backups</p><p className="text-3xl font-bold text-blue-600">{stats.total}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Completed</p><p className="text-3xl font-bold text-green-600">{stats.completed}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Failed</p><p className="text-3xl font-bold text-red-600">{stats.failed}</p></Card>
          <Card className="p-4">
            <p className="text-sm text-gray-500">Last Backup</p>
            <p className="text-sm font-bold text-gray-900 mt-1">
              {stats.lastBackup ? new Date(stats.lastBackup.completedAt).toLocaleString() : 'Never'}
            </p>
          </Card>
        </div>
      )}

      <Card className="p-4 border-blue-200 bg-blue-50">
        <h3 className="font-semibold text-blue-900 mb-1">💡 Backup Schedule</h3>
        <p className="text-sm text-blue-700">For production deployments, configure automated backups via cron or your cloud provider. Full backups recommended weekly, incremental daily.</p>
      </Card>

      <Card>
        <div className="p-4 border-b font-semibold">Backup History</div>
        {loading ? (
          <div className="p-12 text-center text-gray-400">Loading...</div>
        ) : backups.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <div className="text-4xl mb-3">💾</div>
            <p>No backups yet</p>
            <Button className="mt-4" onClick={() => triggerBackup('FULL')}>Create First Backup</Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Size</th>
                  <th className="px-4 py-3 text-left">Location</th>
                  <th className="px-4 py-3 text-left">Started</th>
                  <th className="px-4 py-3 text-left">Completed</th>
                </tr>
              </thead>
              <tbody>
                {backups.map(b => (
                  <tr key={b.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className="font-medium">{b.type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[b.status] || 'bg-gray-100'}`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatBytes(b.size)}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs font-mono">{b.location || '—'}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(b.startedAt).toLocaleString()}</td>
                    <td className="px-4 py-3 text-gray-500">{b.completedAt ? new Date(b.completedAt).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
