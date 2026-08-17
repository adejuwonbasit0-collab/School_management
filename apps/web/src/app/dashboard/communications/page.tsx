'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

type Tab = 'broadcasts' | 'inbox' | 'sent' | 'compose';

const CHANNEL_OPTIONS = ['in_app', 'email', 'sms'];
const AUDIENCE_TYPES = ['all', 'students', 'parents', 'staff'];

interface Broadcast { id: string; subject?: string; body: string; status: string; recipientCount: number; sentAt?: string; createdAt: string }
interface Message { id: string; subject?: string; body: string; isRead: boolean; createdAt: string; sender?: any; receiver?: any; replies?: any[] }

export default function CommunicationsPage() {
  const [tab, setTab] = useState<Tab>('broadcasts');
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [inbox, setInbox] = useState<Message[]>([]);
  const [sent, setSent] = useState<Message[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedMsg, setSelectedMsg] = useState<Message | null>(null);

  // Broadcast form
  const [bForm, setBForm] = useState({ subject: '', body: '', audienceType: 'all', channels: ['in_app'] });
  const [bSaving, setBSaving] = useState(false);

  // Compose form
  const [cForm, setCForm] = useState({ receiverId: '', subject: '', body: '' });
  const [cSaving, setCSaving] = useState(false);

  useEffect(() => { loadUnread(); }, []);
  useEffect(() => { loadTab(tab); }, [tab]);

  const loadUnread = async () => {
    try {
      const res = await apiClient.get('/communications/messages/unread-count');
      setUnread(res.data?.count || 0);
    } catch (e) { /* silent */ }
  };

  const loadTab = async (t: Tab) => {
    if (t === 'compose') return;
    setLoading(true);
    try {
      if (t === 'broadcasts') {
        const res = await apiClient.get('/communications/broadcasts');
        setBroadcasts(res.data?.data?.data || []);
      } else if (t === 'inbox') {
        const res = await apiClient.get('/communications/messages/inbox');
        setInbox(res.data?.data || []);
        loadUnread();
      } else if (t === 'sent') {
        const res = await apiClient.get('/communications/messages/sent');
        setSent(res.data?.data || []);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const sendBroadcast = async () => {
    if (!bForm.body.trim()) return alert('Message body required');
    setBSaving(true);
    try {
      const created = await apiClient.post('/communications/broadcasts', {
        subject: bForm.subject,
        body: bForm.body,
        audience: { type: bForm.audienceType },
        channels: bForm.channels,
      });
      await apiClient.post(`/communications/broadcasts/${created.data.id}/send`);
      setBForm({ subject: '', body: '', audienceType: 'all', channels: ['in_app'] });
      setTab('broadcasts');
    } catch (e) { alert('Send failed'); }
    finally { setBSaving(false); }
  };

  const deleteBroadcast = async (id: string) => {
    if (!confirm('Delete this broadcast?')) return;
    try {
      await apiClient.delete(`/communications/broadcasts/${id}`);
      loadTab('broadcasts');
    } catch (e: any) { alert(e?.response?.data?.message || 'Cannot delete sent broadcast'); }
  };

  const openMessage = async (msg: Message) => {
    try {
      const res = await apiClient.get(`/communications/messages/${msg.id}`);
      setSelectedMsg(res.data);
      loadUnread();
    } catch (e) { console.error(e); }
  };

  const sendMessage = async () => {
    if (!cForm.receiverId.trim() || !cForm.body.trim()) return alert('Recipient and message required');
    setCSaving(true);
    try {
      await apiClient.post('/communications/messages', cForm);
      setCForm({ receiverId: '', subject: '', body: '' });
      setTab('sent');
    } catch (e) { alert('Send failed'); }
    finally { setCSaving(false); }
  };

  const toggleChannel = (ch: string) => {
    setBForm(f => ({
      ...f,
      channels: f.channels.includes(ch) ? f.channels.filter(c => c !== ch) : [...f.channels, ch],
    }));
  };

  const STATUS_BADGE: Record<string, string> = {
    sent: 'bg-green-100 text-green-700',
    draft: 'bg-gray-100 text-gray-600',
    scheduled: 'bg-blue-100 text-blue-700',
  };

  const tabs = [
    { key: 'broadcasts' as Tab, label: '📢 Broadcasts' },
    { key: 'inbox' as Tab, label: `📥 Inbox${unread > 0 ? ` (${unread})` : ''}` },
    { key: 'sent' as Tab, label: '📤 Sent' },
    { key: 'compose' as Tab, label: '✏️ Compose' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Communications Center</h1>
          <p className="text-sm text-gray-500">Send broadcasts, messages, and manage notification templates</p>
        </div>
        <Button onClick={() => setTab('broadcasts')}>
          + New Broadcast
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => { setSelectedMsg(null); setTab(t.key); }}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-400">Loading...</div>
      ) : (
        <>
          {/* Broadcasts Tab */}
          {tab === 'broadcasts' && (
            <div className="space-y-4">
              {/* Quick Broadcast Form */}
              <Card className="p-5">
                <h2 className="font-semibold text-gray-900 mb-4">Send Broadcast</h2>
                <div className="space-y-3">
                  <Input
                    placeholder="Subject (optional)"
                    value={bForm.subject}
                    onChange={e => setBForm(f => ({ ...f, subject: e.target.value }))}
                  />
                  <textarea
                    className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={4}
                    placeholder="Write your message..."
                    value={bForm.body}
                    onChange={e => setBForm(f => ({ ...f, body: e.target.value }))}
                  />
                  <div className="flex items-center gap-6 flex-wrap">
                    <div>
                      <label className="text-sm font-medium mr-2">Audience:</label>
                      <select
                        className="border rounded px-2 py-1 text-sm"
                        value={bForm.audienceType}
                        onChange={e => setBForm(f => ({ ...f, audienceType: e.target.value }))}
                      >
                        {AUDIENCE_TYPES.map(a => <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>)}
                      </select>
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium">Channels:</label>
                      {CHANNEL_OPTIONS.map(ch => (
                        <label key={ch} className="flex items-center gap-1 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={bForm.channels.includes(ch)}
                            onChange={() => toggleChannel(ch)}
                          />
                          {ch.replace('_', ' ')}
                        </label>
                      ))}
                    </div>
                    <div className="flex-1" />
                    <Button onClick={sendBroadcast} disabled={bSaving}>
                      {bSaving ? 'Sending...' : '📢 Send Now'}
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Broadcast History */}
              <Card>
                <div className="p-4 border-b font-semibold">Broadcast History</div>
                {broadcasts.length === 0 ? (
                  <div className="p-12 text-center text-gray-400">No broadcasts sent yet</div>
                ) : (
                  <div className="divide-y">
                    {broadcasts.map(b => (
                      <div key={b.id} className="px-5 py-4 flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[b.status] || 'bg-gray-100'}`}>
                              {b.status}
                            </span>
                            {b.subject && <span className="font-medium text-gray-900">{b.subject}</span>}
                          </div>
                          <p className="text-sm text-gray-600 line-clamp-2">{b.body}</p>
                          <p className="text-xs text-gray-400 mt-1">
                            {b.recipientCount} recipients · {new Date(b.createdAt).toLocaleString()}
                          </p>
                        </div>
                        {b.status !== 'sent' && (
                          <button
                            onClick={() => deleteBroadcast(b.id)}
                            className="text-red-400 hover:text-red-600 text-sm ml-4"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Inbox Tab */}
          {tab === 'inbox' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="md:col-span-1 overflow-y-auto max-h-[600px]">
                {inbox.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    <div className="text-3xl mb-2">📥</div>
                    <p>No messages</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {inbox.map(msg => (
                      <button
                        key={msg.id}
                        onClick={() => openMessage(msg)}
                        className={`w-full text-left px-4 py-3 hover:bg-gray-50 ${selectedMsg?.id === msg.id ? 'bg-blue-50' : ''}`}
                      >
                        <div className="flex items-start gap-2">
                          {!msg.isRead && <span className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0" />}
                          <div className="min-w-0 flex-1">
                            <p className={`text-sm truncate ${!msg.isRead ? 'font-semibold' : ''}`}>
                              {msg.sender?.firstName} {msg.sender?.lastName}
                            </p>
                            <p className="text-xs text-gray-500 truncate">{msg.subject || msg.body.slice(0, 40)}</p>
                            <p className="text-xs text-gray-400">{new Date(msg.createdAt).toLocaleDateString()}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </Card>
              <Card className="md:col-span-2 p-5">
                {selectedMsg ? (
                  <div>
                    <div className="mb-4 pb-4 border-b">
                      <h2 className="text-lg font-semibold">{selectedMsg.subject || '(No Subject)'}</h2>
                      <p className="text-sm text-gray-500">
                        From: {selectedMsg.sender?.firstName} {selectedMsg.sender?.lastName} · {new Date(selectedMsg.createdAt).toLocaleString()}
                      </p>
                    </div>
                    <div className="text-gray-800 whitespace-pre-wrap text-sm leading-relaxed">{selectedMsg.body}</div>
                    {(selectedMsg.replies || []).map((r: any) => (
                      <div key={r.id} className="mt-4 pt-4 border-t">
                        <p className="text-xs text-gray-500 mb-1">
                          {r.sender?.firstName} {r.sender?.lastName} · {new Date(r.createdAt).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-800">{r.body}</p>
                      </div>
                    ))}
                    <div className="mt-5 pt-4 border-t space-y-2">
                      <textarea
                        className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                        placeholder="Write a reply..."
                        value={cForm.body}
                        onChange={e => setCForm(f => ({ ...f, body: e.target.value }))}
                      />
                      <Button size="sm" onClick={async () => {
                        if (!cForm.body) return;
                        await apiClient.post('/communications/messages', {
                          receiverId: selectedMsg.sender?.id,
                          body: cForm.body,
                          parentId: selectedMsg.id,
                        });
                        setCForm(f => ({ ...f, body: '' }));
                        openMessage(selectedMsg);
                      }}>Reply</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <div className="text-4xl mb-2">💬</div>
                      <p>Select a message to read</p>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Sent Tab */}
          {tab === 'sent' && (
            <Card>
              {sent.length === 0 ? (
                <div className="p-12 text-center text-gray-400">
                  <div className="text-4xl mb-2">📤</div>
                  <p>No sent messages</p>
                </div>
              ) : (
                <div className="divide-y">
                  {sent.map(msg => (
                    <div key={msg.id} className="px-5 py-4">
                      <div className="flex justify-between">
                        <p className="font-medium">To: {msg.receiver?.firstName} {msg.receiver?.lastName}</p>
                        <p className="text-sm text-gray-400">{new Date(msg.createdAt).toLocaleString()}</p>
                      </div>
                      {msg.subject && <p className="text-sm font-medium text-gray-700 mt-0.5">{msg.subject}</p>}
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">{msg.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Compose Tab */}
          {tab === 'compose' && (
            <Card className="p-6 max-w-2xl">
              <h2 className="text-lg font-semibold mb-4">New Message</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Recipient User ID *</label>
                  <Input
                    placeholder="Paste user ID or search users..."
                    value={cForm.receiverId}
                    onChange={e => setCForm(f => ({ ...f, receiverId: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Subject</label>
                  <Input
                    placeholder="Message subject"
                    value={cForm.subject}
                    onChange={e => setCForm(f => ({ ...f, subject: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Message *</label>
                  <textarea
                    className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={6}
                    placeholder="Type your message..."
                    value={cForm.body}
                    onChange={e => setCForm(f => ({ ...f, body: e.target.value }))}
                  />
                </div>
                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setTab('inbox')}>Cancel</Button>
                  <Button onClick={sendMessage} disabled={cSaving}>
                    {cSaving ? 'Sending...' : '📤 Send Message'}
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
