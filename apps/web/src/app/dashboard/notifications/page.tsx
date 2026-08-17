'use client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Bell, CheckCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import { cn } from '@/lib/utils';

export default function NotificationsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['all-notifications'], queryFn: () => api.get<any>('/v1/notifications?limit=50') });
  const markAllMutation = useMutation({
    mutationFn: () => api.put('/v1/notifications/read-all', {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['all-notifications'] }),
  });
  const notifications = data?.data || [];
  const unread = notifications.filter((n: any) => !n.readAt).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="section-title">Notifications</h1><p className="section-subtitle">{unread > 0 ? `${unread} unread` : 'All caught up'}</p></div>
        {unread > 0 && <Button variant="outline" size="sm" onClick={() => markAllMutation.mutate()}><CheckCheck className="w-4 h-4 mr-2" />Mark all read</Button>}
      </div>
      <div className="space-y-2">
        {notifications.length === 0 && (
          <Card><CardContent className="py-16 text-center text-muted-foreground"><Bell className="w-12 h-12 mx-auto mb-3 opacity-20" />No notifications</CardContent></Card>
        )}
        {notifications.map((n: any) => (
          <Card key={n.id} className={cn('shadow-card transition-colors', !n.readAt && 'border-primary/30 bg-primary/5')}>
            <CardContent className="pt-3 pb-3">
              <div className="flex items-start gap-3">
                <div className={cn('w-2 h-2 rounded-full mt-2 flex-shrink-0', !n.readAt ? 'bg-primary' : 'bg-transparent')} />
                <div className="flex-1">
                  <p className="font-medium text-sm">{n.title}</p>
                  <p className="text-sm text-muted-foreground">{n.body}</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">{formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}</p>
                </div>
                <Badge variant="outline" className="text-xs shrink-0">{n.type}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
