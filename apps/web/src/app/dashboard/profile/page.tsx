'use client';
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { User, Shield, Key, Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api-client';
import { useAuth, useAuthStore } from '@/store/auth.store';
import toast from 'react-hot-toast';

export default function ProfilePage() {
  const { user } = useAuth();
  const setUser = useAuthStore((s) => s.setUser);
  const [firstName, setFirstName] = useState(user?.firstName || '');
  const [lastName, setLastName] = useState(user?.lastName || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const updateMutation = useMutation({
    mutationFn: () => api.put('/v1/users/me', { firstName, lastName }),
    onSuccess: (data: any) => { setUser(data); toast.success('Profile updated'); },
  });

  const passwordMutation = useMutation({
    mutationFn: () => api.put('/v1/auth/change-password', { currentPassword, newPassword }),
    onSuccess: () => { toast.success('Password changed'); setCurrentPassword(''); setNewPassword(''); },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <div><h1 className="section-title">My Profile</h1><p className="section-subtitle">Manage your personal information</p></div>

      <Tabs defaultValue="personal">
        <TabsList>
          <TabsTrigger value="personal"><User className="w-4 h-4 mr-1.5" />Personal</TabsTrigger>
          <TabsTrigger value="security"><Shield className="w-4 h-4 mr-1.5" />Security</TabsTrigger>
        </TabsList>

        <TabsContent value="personal" className="mt-4">
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div className="flex items-center gap-4">
                <Avatar className="w-20 h-20">
                  <AvatarImage src={user?.avatar} />
                  <AvatarFallback className="text-2xl bg-primary/10 text-primary font-bold">
                    {user?.firstName?.[0]}{user?.lastName?.[0]}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="text-xl font-bold">{user?.firstName} {user?.lastName}</h2>
                  <p className="text-muted-foreground text-sm">{user?.email}</p>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {user?.roles?.map((r) => <Badge key={r} variant="secondary" className="text-xs">{r}</Badge>)}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5"><Label>First Name</Label><Input value={firstName} onChange={(e) => setFirstName(e.target.value)} /></div>
                <div className="space-y-1.5"><Label>Last Name</Label><Input value={lastName} onChange={(e) => setLastName(e.target.value)} /></div>
                <div className="space-y-1.5 col-span-2"><Label>Email</Label><Input value={user?.email} disabled /></div>
                <div className="space-y-1.5 col-span-2"><Label>School</Label><Input value={user?.school?.name || ''} disabled /></div>
              </div>
              <Button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Change Password</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5"><Label>Current Password</Label><Input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>New Password</Label><Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></div>
              <Button onClick={() => passwordMutation.mutate()} disabled={!currentPassword || !newPassword || passwordMutation.isPending}>
                {passwordMutation.isPending ? 'Changing...' : 'Change Password'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
