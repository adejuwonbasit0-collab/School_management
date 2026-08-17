'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface Folder { id: string; name: string; description?: string; _count?: { children: number; documents: number } }
interface Doc {
  id: string; name: string; fileType: string; size?: number; mimeType?: string;
  url: string; tags: string[]; createdAt: string; version: number;
  folder?: { name: string };
}

const FILE_ICONS: Record<string, string> = {
  pdf: '📄', doc: '📝', docx: '📝', xls: '📊', xlsx: '📊',
  ppt: '📑', pptx: '📑', jpg: '🖼️', jpeg: '🖼️', png: '🖼️',
  mp4: '🎬', mp3: '🎵', zip: '📦',
};

const fileIcon = (type: string) => FILE_ICONS[type.toLowerCase()] || '📎';
const formatSize = (bytes?: number) => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

export default function DocumentsPage() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [currentFolder, setCurrentFolder] = useState<Folder | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<Folder[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);

  // Modals
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [uploadForm, setUploadForm] = useState({ name: '', url: '', fileType: 'pdf', description: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadStats();
    loadFolder(null);
  }, []);

  const loadStats = async () => {
    try {
      const res = await apiClient.get('/documents/stats');
      setStats(res.data);
    } catch (e) { console.error(e); }
  };

  const loadFolder = async (folder: Folder | null) => {
    setLoading(true);
    setCurrentFolder(folder);
    try {
      const [folderRes, docRes] = await Promise.all([
        apiClient.get(`/documents/folders${folder ? `?parentId=${folder.id}` : ''}`),
        apiClient.get(`/documents?${folder ? `folderId=${folder.id}` : 'folderId='}&limit=50`),
      ]);
      setFolders(folderRes.data?.data || []);
      setDocs(docRes.data?.data?.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const navigateToFolder = (folder: Folder) => {
    setBreadcrumb(prev => [...prev, ...(currentFolder ? [currentFolder] : [])]);
    loadFolder(folder);
  };

  const navigateBack = (idx: number) => {
    const target = idx === -1 ? null : breadcrumb[idx];
    setBreadcrumb(prev => prev.slice(0, idx === -1 ? 0 : idx));
    loadFolder(target);
  };

  const createFolder = async () => {
    if (!newFolderName.trim()) return;
    setSaving(true);
    try {
      await apiClient.post('/documents/folders', {
        name: newFolderName,
        parentId: currentFolder?.id,
      });
      setShowNewFolder(false);
      setNewFolderName('');
      loadFolder(currentFolder);
    } catch (e) { alert('Failed to create folder'); }
    finally { setSaving(false); }
  };

  const deleteFolder = async (id: string) => {
    if (!confirm('Delete this folder? It must be empty.')) return;
    try {
      await apiClient.delete(`/documents/folders/${id}`);
      loadFolder(currentFolder);
    } catch (e: any) {
      alert(e?.response?.data?.message || 'Cannot delete folder');
    }
  };

  const uploadDoc = async () => {
    if (!uploadForm.name || !uploadForm.url) return alert('Name and URL required');
    setSaving(true);
    try {
      await apiClient.post('/documents', {
        ...uploadForm,
        folderId: currentFolder?.id,
      });
      setShowUpload(false);
      setUploadForm({ name: '', url: '', fileType: 'pdf', description: '' });
      loadFolder(currentFolder);
      loadStats();
    } catch (e) { alert('Upload failed'); }
    finally { setSaving(false); }
  };

  const deleteDoc = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await apiClient.delete(`/documents/${id}`);
      loadFolder(currentFolder);
      loadStats();
    } catch (e) { alert('Delete failed'); }
  };

  const filteredDocs = docs.filter(d =>
    !search || d.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Management</h1>
          <p className="text-sm text-gray-500">Store and organise school documents, staff files, and student records</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowNewFolder(true)}>📁 New Folder</Button>
          <Button onClick={() => setShowUpload(true)}>⬆ Add Document</Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-500">Total Documents</p>
            <p className="text-3xl font-bold text-blue-600">{stats.totalDocuments}</p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-500">Total Folders</p>
            <p className="text-3xl font-bold text-green-600">{stats.totalFolders}</p>
          </Card>
          {stats.byType?.slice(0, 2).map((t: any) => (
            <Card key={t.type} className="p-4">
              <p className="text-sm text-gray-500">{t.type.toUpperCase()} Files</p>
              <p className="text-3xl font-bold text-purple-600">{t.count}</p>
              <p className="text-xs text-gray-400">{formatSize(t.totalSize)}</p>
            </Card>
          ))}
        </div>
      )}

      <Card>
        {/* Breadcrumb + Search */}
        <div className="p-4 border-b flex items-center gap-4 flex-wrap">
          <nav className="flex items-center gap-1 text-sm flex-1">
            <button onClick={() => navigateBack(-1)} className="text-blue-600 hover:underline font-medium">
              📁 Root
            </button>
            {breadcrumb.map((b, i) => (
              <span key={b.id} className="flex items-center gap-1">
                <span className="text-gray-400">/</span>
                <button onClick={() => navigateBack(i)} className="text-blue-600 hover:underline">{b.name}</button>
              </span>
            ))}
            {currentFolder && (
              <span className="flex items-center gap-1">
                <span className="text-gray-400">/</span>
                <span className="text-gray-900 font-medium">{currentFolder.name}</span>
              </span>
            )}
          </nav>
          <Input
            placeholder="Search files..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-56"
          />
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400">Loading...</div>
        ) : (
          <div className="p-4">
            {/* Folders */}
            {folders.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Folders</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  {folders.map(folder => (
                    <div key={folder.id} className="group relative">
                      <button
                        onClick={() => navigateToFolder(folder)}
                        className="w-full flex flex-col items-center p-4 rounded-lg border hover:border-blue-300 hover:bg-blue-50 transition-colors text-center"
                      >
                        <span className="text-3xl mb-2">📁</span>
                        <span className="text-sm font-medium text-gray-800 truncate w-full">{folder.name}</span>
                        <span className="text-xs text-gray-400 mt-1">
                          {folder._count?.documents || 0} files
                        </span>
                      </button>
                      <button
                        onClick={() => deleteFolder(folder.id)}
                        className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs p-1"
                        title="Delete folder"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Files */}
            {filteredDocs.length > 0 ? (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Files</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left">Name</th>
                        <th className="px-3 py-2 text-left">Type</th>
                        <th className="px-3 py-2 text-left">Size</th>
                        <th className="px-3 py-2 text-left">Version</th>
                        <th className="px-3 py-2 text-left">Uploaded</th>
                        <th className="px-3 py-2 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDocs.map(doc => (
                        <tr key={doc.id} className="border-b hover:bg-gray-50">
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-2">
                              <span className="text-xl">{fileIcon(doc.fileType)}</span>
                              <div>
                                <div className="font-medium text-gray-900">{doc.name}</div>
                                {doc.tags.length > 0 && (
                                  <div className="flex gap-1 mt-0.5">
                                    {doc.tags.slice(0, 3).map(t => (
                                      <span key={t} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{t}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-3 text-gray-500 uppercase text-xs">{doc.fileType}</td>
                          <td className="px-3 py-3 text-gray-500">{formatSize(doc.size)}</td>
                          <td className="px-3 py-3 text-gray-500">v{doc.version}</td>
                          <td className="px-3 py-3 text-gray-500">
                            {new Date(doc.createdAt).toLocaleDateString()}
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex gap-2">
                              <a href={doc.url} target="_blank" rel="noreferrer"
                                className="text-blue-600 hover:underline text-xs">
                                View
                              </a>
                              <button onClick={() => deleteDoc(doc.id, doc.name)}
                                className="text-red-500 hover:underline text-xs">
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              folders.length === 0 && (
                <div className="text-center py-16 text-gray-400">
                  <div className="text-5xl mb-4">📂</div>
                  <p className="font-medium">This folder is empty</p>
                  <p className="text-sm mt-1">Create a subfolder or upload a document</p>
                </div>
              )
            )}
          </div>
        )}
      </Card>

      {/* New Folder Modal */}
      {showNewFolder && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h2 className="text-lg font-bold mb-4">New Folder</h2>
            <Input
              placeholder="Folder name"
              value={newFolderName}
              onChange={e => setNewFolderName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createFolder()}
              autoFocus
            />
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => setShowNewFolder(false)}>Cancel</Button>
              <Button onClick={createFolder} disabled={saving}>
                {saving ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Document Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Add Document</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">Document Name *</label>
                <Input
                  placeholder="e.g. Student Handbook 2024"
                  value={uploadForm.name}
                  onChange={e => setUploadForm(f => ({ ...f, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">File URL *</label>
                <Input
                  placeholder="https://..."
                  value={uploadForm.url}
                  onChange={e => setUploadForm(f => ({ ...f, url: e.target.value }))}
                />
                <p className="text-xs text-gray-400 mt-1">Paste a Cloudinary/S3/CDN URL</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">File Type</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={uploadForm.fileType}
                  onChange={e => setUploadForm(f => ({ ...f, fileType: e.target.value }))}
                >
                  {['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'png', 'mp4', 'zip', 'other'].map(t => (
                    <option key={t} value={t}>{t.toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <Input
                  placeholder="Optional description"
                  value={uploadForm.description}
                  onChange={e => setUploadForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <Button variant="outline" onClick={() => setShowUpload(false)}>Cancel</Button>
              <Button onClick={uploadDoc} disabled={saving}>
                {saving ? 'Saving...' : 'Save Document'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
