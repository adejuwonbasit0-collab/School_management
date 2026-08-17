'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const FONT_OPTIONS = ['Inter', 'Poppins', 'Roboto', 'Open Sans', 'Lato', 'Montserrat', 'Nunito', 'DM Sans'];
const COLOR_PRESETS = [
  { name: 'EduBlue', primary: '#1a56db', secondary: '#7c3aed', accent: '#059669' },
  { name: 'Forest', primary: '#166534', secondary: '#0369a1', accent: '#d97706' },
  { name: 'Royal', primary: '#4c1d95', secondary: '#b45309', accent: '#0891b2' },
  { name: 'Crimson', primary: '#991b1b', secondary: '#1d4ed8', accent: '#059669' },
  { name: 'Slate', primary: '#1e293b', secondary: '#0f172a', accent: '#3b82f6' },
];

export default function CustomizationPage() {
  const [theme, setTheme] = useState({ primaryColor: '#1a56db', secondaryColor: '#7c3aed', accentColor: '#059669', fontFamily: 'Inter', logoUrl: '', footerText: '', customCss: '' });
  const [branding, setBranding] = useState({ name: '', address: '', phone: '', email: '', website: '' });
  const [pages, setPages] = useState<any[]>([]);
  const [tab, setTab] = useState<'theme' | 'branding' | 'pages'>('theme');
  const [saving, setSaving] = useState(false);
  const [showPageForm, setShowPageForm] = useState(false);
  const [pageForm, setPageForm] = useState({ slug: '', title: '', content: { blocks: [] }, isPublished: false });

  useEffect(() => {
    apiClient.get('/customization/theme').then(r => setTheme(t => ({ ...t, ...(r.data?.data || {}) }))).catch(console.error);
    apiClient.get('/customization/branding').then(r => { if (r.data?.data?.school) setBranding(r.data.data.school); }).catch(console.error);
    apiClient.get('/customization/pages').then(r => setPages(r.data?.data || [])).catch(console.error);
  }, []);

  const saveTheme = async () => {
    setSaving(true);
    try { await apiClient.put('/customization/theme', theme); alert('Theme saved!'); }
    catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const saveBranding = async () => {
    setSaving(true);
    try { await apiClient.put('/customization/branding', branding); alert('Branding saved!'); }
    catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const savePage = async () => {
    setSaving(true);
    try {
      await apiClient.put(`/customization/pages/${pageForm.slug}`, pageForm);
      setShowPageForm(false);
      const r = await apiClient.get('/customization/pages');
      setPages(r.data?.data || []);
    } catch (e) { alert('Save failed'); }
    finally { setSaving(false); }
  };

  const deletePage = async (slug: string) => {
    if (!confirm('Delete this page?')) return;
    await apiClient.delete(`/customization/pages/${slug}`);
    setPages(prev => prev.filter(p => p.slug !== slug));
  };

  const applyPreset = (preset: any) => {
    setTheme(t => ({ ...t, primaryColor: preset.primary, secondaryColor: preset.secondary, accentColor: preset.accent }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Customization Center</h1>
        <p className="text-sm text-gray-500">Configure branding, themes, and custom pages without editing code</p>
      </div>

      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[{ key: 'theme' as const, label: '🎨 Theme' }, { key: 'branding' as const, label: '🏫 Branding' }, { key: 'pages' as const, label: '📄 Pages' }].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Theme Tab */}
      {tab === 'theme' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6 space-y-5">
            <h2 className="font-semibold">Color Presets</h2>
            <div className="flex flex-wrap gap-2">
              {COLOR_PRESETS.map(preset => (
                <button key={preset.name} onClick={() => applyPreset(preset)}
                  className="flex items-center gap-2 px-3 py-2 border rounded-lg hover:border-blue-400 text-sm">
                  <div className="flex gap-0.5">
                    <span className="w-4 h-4 rounded-full" style={{ backgroundColor: preset.primary }} />
                    <span className="w-4 h-4 rounded-full" style={{ backgroundColor: preset.secondary }} />
                    <span className="w-4 h-4 rounded-full" style={{ backgroundColor: preset.accent }} />
                  </div>
                  {preset.name}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Primary', key: 'primaryColor' },
                { label: 'Secondary', key: 'secondaryColor' },
                { label: 'Accent', key: 'accentColor' },
              ].map(c => (
                <div key={c.key}>
                  <label className="text-sm font-medium block mb-1">{c.label}</label>
                  <div className="flex gap-2 items-center">
                    <input type="color" value={(theme as any)[c.key]} onChange={e => setTheme(t => ({ ...t, [c.key]: e.target.value }))} className="w-10 h-10 rounded cursor-pointer border" />
                    <Input value={(theme as any)[c.key]} onChange={e => setTheme(t => ({ ...t, [c.key]: e.target.value }))} className="font-mono text-xs" />
                  </div>
                </div>
              ))}
            </div>

            <div>
              <label className="text-sm font-medium block mb-1">Font Family</label>
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={theme.fontFamily} onChange={e => setTheme(t => ({ ...t, fontFamily: e.target.value }))}>
                {FONT_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium block mb-1">Logo URL</label>
              <Input placeholder="https://..." value={theme.logoUrl || ''} onChange={e => setTheme(t => ({ ...t, logoUrl: e.target.value }))} />
            </div>

            <div>
              <label className="text-sm font-medium block mb-1">Footer Text</label>
              <Input placeholder="© 2024 School Name. All rights reserved." value={theme.footerText || ''} onChange={e => setTheme(t => ({ ...t, footerText: e.target.value }))} />
            </div>

            <div>
              <label className="text-sm font-medium block mb-1">Custom CSS (Advanced)</label>
              <textarea className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-none" rows={4} placeholder=".my-class { color: red; }" value={theme.customCss || ''} onChange={e => setTheme(t => ({ ...t, customCss: e.target.value }))} />
            </div>

            <Button onClick={saveTheme} disabled={saving} className="w-full">{saving ? 'Saving...' : '💾 Save Theme'}</Button>
          </Card>

          {/* Live Preview */}
          <Card className="p-6">
            <h2 className="font-semibold mb-4">Live Preview</h2>
            <div className="rounded-xl overflow-hidden border shadow-sm" style={{ fontFamily: theme.fontFamily }}>
              {/* Nav preview */}
              <div className="p-3 flex items-center gap-3" style={{ backgroundColor: theme.primaryColor }}>
                <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center text-white text-xs font-bold">E</div>
                <span className="text-white font-semibold text-sm">EduCore</span>
                <div className="ml-auto flex gap-3">
                  {['Dashboard', 'Students', 'Finance'].map(item => <span key={item} className="text-white/80 text-xs">{item}</span>)}
                </div>
              </div>
              {/* Content preview */}
              <div className="p-5 bg-white">
                <div className="text-sm font-semibold mb-3" style={{ color: theme.primaryColor }}>Dashboard Overview</div>
                <div className="grid grid-cols-3 gap-2 mb-3">
                  {['Students', 'Revenue', 'Staff'].map((label, i) => (
                    <div key={label} className="rounded-lg p-3 text-center" style={{ backgroundColor: [theme.primaryColor, theme.secondaryColor, theme.accentColor][i] + '20' }}>
                      <div className="text-xl font-bold" style={{ color: [theme.primaryColor, theme.secondaryColor, theme.accentColor][i] }}>{(i + 1) * 124}</div>
                      <div className="text-xs text-gray-500">{label}</div>
                    </div>
                  ))}
                </div>
                <div className="h-2 rounded-full mb-1" style={{ backgroundColor: theme.primaryColor }} />
                <div className="h-2 rounded-full w-3/4" style={{ backgroundColor: theme.secondaryColor + '60' }} />
              </div>
              {/* Footer */}
              <div className="px-4 py-2 text-xs text-center text-gray-400" style={{ borderTop: `2px solid ${theme.accentColor}` }}>
                {theme.footerText || '© 2024 EduCore. All rights reserved.'}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Branding Tab */}
      {tab === 'branding' && (
        <Card className="p-6 max-w-xl">
          <h2 className="font-semibold mb-5">School Information</h2>
          <div className="space-y-4">
            {[
              { label: 'School Name', key: 'name', placeholder: 'Springfield Academy' },
              { label: 'Address', key: 'address', placeholder: '123 School Lane, City' },
              { label: 'Phone', key: 'phone', placeholder: '+234 800 000 0000' },
              { label: 'Email', key: 'email', placeholder: 'admin@school.edu' },
              { label: 'Website', key: 'website', placeholder: 'https://school.edu' },
            ].map(f => (
              <div key={f.key}>
                <label className="text-sm font-medium block mb-1">{f.label}</label>
                <Input placeholder={f.placeholder} value={(branding as any)[f.key] || ''} onChange={e => setBranding(b => ({ ...b, [f.key]: e.target.value }))} />
              </div>
            ))}
            <Button onClick={saveBranding} disabled={saving} className="w-full">{saving ? 'Saving...' : '💾 Save Branding'}</Button>
          </div>
        </Card>
      )}

      {/* Pages Tab */}
      {tab === 'pages' && (
        <div className="space-y-4">
          <div className="flex justify-end"><Button onClick={() => { setPageForm({ slug: '', title: '', content: { blocks: [] }, isPublished: false }); setShowPageForm(true); }}>+ New Page</Button></div>
          {pages.length === 0 ? (
            <Card className="p-12 text-center text-gray-400"><div className="text-4xl mb-3">📄</div><p>No custom pages yet</p></Card>
          ) : (
            <div className="grid gap-3">
              {pages.map(p => (
                <Card key={p.slug} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{p.title}</p>
                    <p className="text-sm text-gray-500">/{p.slug}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${p.isPublished ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>{p.isPublished ? 'Published' : 'Draft'}</span>
                    <Button size="sm" variant="outline" onClick={() => { setPageForm(p); setShowPageForm(true); }}>Edit</Button>
                    <Button size="sm" variant="outline" onClick={() => deletePage(p.slug)} className="text-red-600">Delete</Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Page Form Modal */}
      {showPageForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl">
            <h2 className="text-lg font-bold mb-4">Custom Page</h2>
            <div className="space-y-3">
              <div><label className="text-sm font-medium">Slug (URL path)</label><Input placeholder="about-us" value={pageForm.slug} onChange={e => setPageForm(f => ({ ...f, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') }))} /></div>
              <div><label className="text-sm font-medium">Page Title</label><Input placeholder="About Us" value={pageForm.title} onChange={e => setPageForm(f => ({ ...f, title: e.target.value }))} /></div>
              <div><label className="text-sm font-medium">Content (HTML/Markdown)</label>
                <textarea className="w-full border rounded-lg px-3 py-2 text-sm resize-none" rows={6} placeholder="<h1>Welcome to our school</h1><p>Content here...</p>"
                  onChange={e => setPageForm(f => ({ ...f, content: { blocks: [{ type: 'html', content: e.target.value }] } }))} />
              </div>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={pageForm.isPublished} onChange={e => setPageForm(f => ({ ...f, isPublished: e.target.checked }))} />
                Published (visible to users)
              </label>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowPageForm(false)}>Cancel</Button>
              <Button onClick={savePage} disabled={saving}>{saving ? 'Saving...' : 'Save Page'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
