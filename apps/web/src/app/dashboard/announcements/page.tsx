'use client';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, format } from 'date-fns';
import { Megaphone, Plus, AlertCircle, Bell, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const PRIORITY_CONFIG: Record<string, { class: string; icon: any }> = {
  high: { class: 'badge-danger', icon: AlertCircle },
  normal: { class: 'badge-info', icon: Bell },
  low: { class: 'badge-neutral', icon: Info },
};

export default function AnnouncementsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [announcementTitle, setAnnouncementTitle] = useState('');
  const [content, setContent] = useState('');
  const [priority, setPriority] = useState('normal');
  const [isPublished, setIsPublished] = useState(true);
  const { user, hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ['announcements-list'],
    queryFn: () => api.get<any>('/v1/notifications/announcements'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/notifications/announcements', {
      title: announcementTitle, content, priority, isPublished,
      audience: ['all'],
    }),
    onSuccess: () => {
      toast.success('Announcement created');
      qc.invalidateQueries({ queryKey: ['announcements-list'] });
      setCreateOpen(false);
      setAnnouncementTitle(''); setContent('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const announcements = data?.data || data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="section-title">Announcements</h1><p className="section-subtitle">Broadcast messages to the school community</p></div>
        {hasPermission('notifications:announcements:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}><Plus className="w-4 h-4 mr-2" />New Announcement</Button>
        )}
      </div>

      <div className="space-y-4">
        {announcements.length === 0 && (
          <Card><CardContent className="py-16 text-center text-muted-foreground">
            <Megaphone className="w-12 h-12 mx-auto mb-3 opacity-20" /><p>No announcements yet</p>
          </CardContent></Card>
        )}
        {announcements.map((a: any) => {
          const cfg = PRIORITY_CONFIG[a.priority] || PRIORITY_CONFIG.normal;
          const Icon = cfg.icon;
          return (
            <Card key={a.id} className={cn('shadow-card border-l-4', a.priority === 'high' ? 'border-l-red-500' : a.priority === 'normal' ? 'border-l-blue-500' : 'border-l-gray-300')}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start gap-3">
                  <div className={cn('p-2 rounded-lg mt-0.5', a.priority === 'high' ? 'bg-red-50' : 'bg-blue-50')}>
                    <Icon className={cn('w-4 h-4', a.priority === 'high' ? 'text-red-600' : 'text-blue-600')} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-semibold">{a.title}</h3>
                      <Badge variant="secondary" className={cn('text-xs', cfg.class)}>{a.priority}</Badge>
                      {!a.isPublished && <Badge variant="outline" className="text-xs">Draft</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{a.content}</p>
                    <p className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(a.createdAt), { addSuffix: true })}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>Create Announcement</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Title *</Label><Input value={announcementTitle} onChange={(e) => setAnnouncementTitle(e.target.value)} placeholder="Announcement title" /></div>
            <div className="space-y-1.5"><Label>Message *</Label><Textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} placeholder="Write your announcement..." /></div>
            <div className="space-y-1.5">
              <Label>Priority</Label>
              <Select defaultValue="normal" onValueChange={setPriority}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High (Urgent)</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={isPublished} onCheckedChange={setIsPublished} />
              <Label>Publish immediately</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!announcementTitle || !content || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Publishing...' : 'Create Announcement'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
