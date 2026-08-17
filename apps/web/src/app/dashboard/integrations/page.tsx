'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Tab = 'providers' | 'api-keys' | 'webhooks';

const WEBHOOK_EVENTS = [
  'student.created', 'student.updated', 'admission.approved', 'fee.paid',
  'attendance.marked', 'result.published', 'staff.added', 'leave.approved',
];

export default function IntegrationsPage() {
  const [tab, setTab] = useState<Tab>('providers');
  const [providers, setProviders] = useState<any[]>([]);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [showWebhookForm, setShowWebhookForm] = useState(false);
  const [keyForm, setKeyForm] = useState({ name: '', permissions: ['read'] });
  const [webhookForm, setWebhookForm] = useState({ name: '', url: '', events: [] as string[] });
  const [configModal, setConfigModal] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiClient.get('/integrations/stats').then(r => setStats(r.data?.data)).catch(console.error);
    loadTab(tab);
  }, []);

  const loadTab = async (t: Tab) => {
    try {
      if (t === 'providers') { const r = await apiClient.get('/integrations/providers'); setProviders(r.data?.data || []); }
      else if (t === 'api-keys') { const r = await apiClient.get('/integrations/api-keys'); setApiKeys(r.data?.data || []); }
      else if (t === 'webhooks') { const r = await apiClient.get('/integrations/webhooks'); setWebhooks(r.data?.data || []); }
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadTab(tab); }, [tab]);

  const createApiKey = async () => {
    setSaving(true);
    try {
      const res = await apiClient.post('/integrations/api-keys', keyForm);
      setNewKey(res.data.rawKey);
      setShowKeyForm(false);
      loadTab('api-keys');
    } catch (e) { alert('Failed to create key'); }
    finally { setSaving(false); }
  };

  const revokeKey = async (id: string) => {
    if (!confirm('Revoke this API key?')) return;
    await apiClient.put(`/integrations/api-keys/${id}/revoke`);
    loadTab('api-keys');
  };

  const createWebhook = async () => {
    setSaving(true);
    try {
      await apiClient.post('/integrations/webhooks', webhookForm);
      setShowWebhookForm(false);
      setWebhookForm({ name: '', url: '', events: [] });
      loadTab('webhooks');
    } catch (e) { alert('Failed to create webhook'); }
    finally { setSaving(false); }
  };

  const testWebhook = async (id: string) => {
    try {
      const res = await apiClient.post(`/integrations/webhooks/${id}/test`);
      alert(res.data.success ? `✅ Webhook delivered (${res.data.status})` : `❌ Failed: ${res.data.error}`);
    } catch (e) { alert('Test failed'); }
  };

  const saveProviderConfig = async () => {
    if (!configModal) return;
    setSaving(true);
    try {
      await apiClient.put(`/integrations/providers/${configModal.provider}`, { config: configModal.config, isActive: true });
      setConfigModal(null);
      loadTab('providers');
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const toggleProvider = async (provider: string, isActive: boolean) => {
    try {
      await apiClient.put(`/integrations/providers/${provider}`, { config: {}, isActive });
      loadTab('providers');
    } catch (e) { console.error(e); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API & Integration Center</h1>
        <p className="text-sm text-gray-500">Manage third-party connections, API keys, and webhooks</p>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="p-4"><p className="text-sm text-gray-500">Active API Keys</p><p className="text-3xl font-bold text-blue-600">{stats.activeApiKeys}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Active Webhooks</p><p className="text-3xl font-bold text-purple-600">{stats.activeWebhooks}</p></Card>
          <Card className="p-4"><p className="text-sm text-gray-500">Connected Services</p><p className="text-3xl font-bold text-green-600">{stats.activeIntegrations}</p></Card>
        </div>
      )}

      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[{ key: 'providers' as Tab, label: '🔌 Integrations' }, { key: 'api-keys' as Tab, label: '🔑 API Keys' }, { key: 'webhooks' as Tab, label: '🪝 Webhooks' }].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Providers */}
      {tab === 'providers' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map(p => (
            <Card key={p.provider} className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{p.icon}</span>
                  <div>
                    <p className="font-semibold">{p.name}</p>
                    <p className="text-sm text-gray-500">{p.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${p.isActive ? 'bg-green-500' : 'bg-gray-300'}`} />
                  <span className="text-xs text-gray-500">{p.isActive ? 'Active' : 'Inactive'}</span>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button size="sm" variant="outline" onClick={() => setConfigModal({ ...p, config: {} })}>Configure</Button>
                {p.isActive
                  ? <Button size="sm" variant="outline" onClick={() => toggleProvider(p.provider, false)} className="text-red-600 border-red-200">Disable</Button>
                  : <Button size="sm" onClick={() => toggleProvider(p.provider, true)}>Enable</Button>}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* API Keys */}
      {tab === 'api-keys' && (
        <div className="space-y-4">
          {newKey && (
            <Card className="p-4 border-green-300 bg-green-50">
              <p className="font-semibold text-green-800 mb-2">✅ API Key Created — Copy it now, it won&apos;t be shown again</p>
              <code className="bg-white border rounded px-3 py-2 text-sm block break-all">{newKey}</code>
              <Button size="sm" className="mt-2" onClick={() => { navigator.clipboard.writeText(newKey); setNewKey(null); }}>Copy & Dismiss</Button>
            </Card>
          )}
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500">{apiKeys.length} keys</p>
            <Button onClick={() => setShowKeyForm(true)}>+ Create API Key</Button>
          </div>
          <Card>
            {apiKeys.length === 0 ? <div className="p-12 text-center text-gray-400">No API keys yet</div> : (
              <div className="divide-y">
                {apiKeys.map(k => (
                  <div key={k.id} className="px-5 py-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium">{k.name}</p>
                      <p className="text-sm text-gray-500 font-mono">{k.keyPrefix}••••••••</p>
                      <p className="text-xs text-gray-400">{k.permissions.join(', ')} · {k.lastUsedAt ? `Last used ${new Date(k.lastUsedAt).toLocaleDateString()}` : 'Never used'}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${k.isActive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{k.isActive ? 'Active' : 'Revoked'}</span>
                      {k.isActive && <Button size="sm" variant="outline" onClick={() => revokeKey(k.id)} className="text-red-600">Revoke</Button>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Webhooks */}
      {tab === 'webhooks' && (
        <div className="space-y-4">
          <div className="flex justify-end"><Button onClick={() => setShowWebhookForm(true)}>+ Add Webhook</Button></div>
          {webhooks.length === 0 ? (
            <Card className="p-12 text-center text-gray-400">
              <div className="text-4xl mb-3">🪝</div><p>No webhooks configured</p>
            </Card>
          ) : (
            <div className="grid gap-4">
              {webhooks.map(wh => (
                <Card key={wh.id} className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{wh.name}</p>
                      <p className="text-sm text-gray-500 font-mono">{wh.url}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {wh.events.map((e: string) => <span key={e} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{e}</span>)}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => testWebhook(wh.id)}>Test</Button>
                      <Button size="sm" variant="outline" onClick={() => { apiClient.delete(`/integrations/webhooks/${wh.id}`); loadTab('webhooks'); }} className="text-red-600">Delete</Button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">{wh._count?.deliveries || 0} deliveries</p>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* API Key Form Modal */}
      {showKeyForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Create API Key</h2>
            <div className="space-y-3">
              <Input placeholder="Key name (e.g. Mobile App)" value={keyForm.name} onChange={e => setKeyForm(f => ({ ...f, name: e.target.value }))} />
              <div>
                <label className="text-sm font-medium">Permissions</label>
                <div className="flex gap-3 mt-1">
                  {['read', 'write', 'admin'].map(p => (
                    <label key={p} className="flex items-center gap-1 text-sm cursor-pointer">
                      <input type="checkbox" checked={keyForm.permissions.includes(p)}
                        onChange={e => setKeyForm(f => ({ ...f, permissions: e.target.checked ? [...f.permissions, p] : f.permissions.filter(x => x !== p) }))} />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowKeyForm(false)}>Cancel</Button>
              <Button onClick={createApiKey} disabled={saving || !keyForm.name}>{saving ? 'Creating...' : 'Create Key'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Webhook Form Modal */}
      {showWebhookForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold mb-4">Add Webhook Endpoint</h2>
            <div className="space-y-3">
              <Input placeholder="Name" value={webhookForm.name} onChange={e => setWebhookForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Endpoint URL (https://...)" value={webhookForm.url} onChange={e => setWebhookForm(f => ({ ...f, url: e.target.value }))} />
              <div>
                <label className="text-sm font-medium block mb-2">Events to listen for:</label>
                <div className="grid grid-cols-2 gap-2">
                  {WEBHOOK_EVENTS.map(ev => (
                    <label key={ev} className="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input type="checkbox" checked={webhookForm.events.includes(ev)}
                        onChange={e => setWebhookForm(f => ({ ...f, events: e.target.checked ? [...f.events, ev] : f.events.filter(x => x !== ev) }))} />
                      {ev}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowWebhookForm(false)}>Cancel</Button>
              <Button onClick={createWebhook} disabled={saving}>{saving ? 'Saving...' : 'Save Webhook'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Provider Config Modal */}
      {configModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-1">{configModal.icon} Configure {configModal.name}</h2>
            <p className="text-sm text-gray-500 mb-4">{configModal.description}</p>
            <div className="space-y-3">
              <div><label className="text-sm font-medium">API Key / Client ID</label><Input placeholder="Enter API key or client ID" onChange={e => setConfigModal((m: any) => ({ ...m, config: { ...m.config, apiKey: e.target.value } }))} /></div>
              <div><label className="text-sm font-medium">Secret / Token</label><Input type="password" placeholder="Enter secret or token" onChange={e => setConfigModal((m: any) => ({ ...m, config: { ...m.config, secret: e.target.value } }))} /></div>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setConfigModal(null)}>Cancel</Button>
              <Button onClick={saveProviderConfig} disabled={saving}>{saving ? 'Saving...' : 'Save & Enable'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
