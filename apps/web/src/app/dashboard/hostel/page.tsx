'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Hotel, Plus, Bed, Users, DoorOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function HostelPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [capacity, setCapacity] = useState('');
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data: hostels, isLoading } = useQuery({
    queryKey: ['hostels'],
    queryFn: () => api.get<any>('/v1/hostel'),
  });

  const { data: residents } = useQuery({
    queryKey: ['hostel-residents'],
    queryFn: () => api.get<any>('/v1/hostel/residents'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/hostel', { name, type, capacity: Number(capacity) }),
    onSuccess: () => {
      toast.success('Hostel created');
      qc.invalidateQueries({ queryKey: ['hostels'] });
      setCreateOpen(false);
      setName(''); setType(''); setCapacity('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const list = hostels || [];
  const totalRooms = list.reduce((s: number, h: any) => s + (h._count?.rooms || 0), 0);
  const totalCapacity = list.reduce((s: number, h: any) => s + h.capacity, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Hostel Management</h1>
          <p className="section-subtitle">Manage boarding houses and resident students</p>
        </div>
        {hasPermission('hostel:hostel:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />New Hostel
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 mb-2"><Hotel className="w-4 h-4 text-blue-600" /></div>
          <p className="text-2xl font-bold">{list.length}</p>
          <p className="text-xs text-muted-foreground">Hostels</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-purple-50 dark:bg-purple-950/30 mb-2"><DoorOpen className="w-4 h-4 text-purple-600" /></div>
          <p className="text-2xl font-bold">{totalRooms}</p>
          <p className="text-xs text-muted-foreground">Total Rooms</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 mb-2"><Users className="w-4 h-4 text-emerald-600" /></div>
          <p className="text-2xl font-bold">{residents?.length || 0}/{totalCapacity}</p>
          <p className="text-xs text-muted-foreground">Current Residents</p>
        </CardContent></Card>
      </div>

      <Tabs defaultValue="hostels">
        <TabsList>
          <TabsTrigger value="hostels">Hostels</TabsTrigger>
          <TabsTrigger value="residents">Residents</TabsTrigger>
        </TabsList>

        <TabsContent value="hostels" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {list.length === 0 && !isLoading && (
              <Card className="col-span-full"><CardContent className="py-16 text-center text-muted-foreground">
                <Hotel className="w-12 h-12 mx-auto mb-3 opacity-20" />No hostels created yet
              </CardContent></Card>
            )}
            {list.map((hostel: any) => (
              <Card key={hostel.id} className="shadow-card">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg"><Hotel className="w-5 h-5 text-blue-600" /></div>
                    <Badge variant="outline">{hostel.type}</Badge>
                  </div>
                  <h3 className="font-semibold">{hostel.name}</h3>
                  <div className="flex justify-between mt-3 text-sm text-muted-foreground">
                    <span>{hostel._count?.rooms || 0} rooms</span>
                    <span>Capacity: {hostel.capacity}</span>
                  </div>
                  {hostel.rooms?.length > 0 && (
                    <div className="mt-3 pt-3 border-t space-y-1">
                      {hostel.rooms.slice(0, 3).map((room: any) => (
                        <div key={room.id} className="flex justify-between text-xs">
                          <span>Room {room.roomNo} ({room.type})</span>
                          <span className="text-muted-foreground">{room._count?.residents || 0}/{room.capacity}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="residents" className="mt-4">
          <Card className="data-table-container shadow-card">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Student</TableHead>
                  <TableHead>Hostel</TableHead>
                  <TableHead>Room</TableHead>
                  <TableHead>Check-in Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(residents || []).length === 0
                  ? <TableRow><TableCell colSpan={4} className="text-center py-12 text-muted-foreground">No residents assigned</TableCell></TableRow>
                  : (residents || []).map((r: any) => (
                      <TableRow key={r.id} className="hover:bg-muted/30">
                        <TableCell className="text-sm font-medium">{r.student?.user?.firstName} {r.student?.user?.lastName}</TableCell>
                        <TableCell className="text-sm">{r.room?.hostel?.name}</TableCell>
                        <TableCell className="text-sm">{r.room?.roomNo}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{format(new Date(r.checkInDate), 'dd MMM yyyy')}</TableCell>
                      </TableRow>
                    ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>New Hostel</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Hostel Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Unity Hostel" /></div>
            <div className="space-y-1.5">
              <Label>Type</Label>
              <Select onValueChange={setType}>
                <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Boys">Boys</SelectItem>
                  <SelectItem value="Girls">Girls</SelectItem>
                  <SelectItem value="Mixed">Mixed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label>Capacity *</Label><Input type="number" value={capacity} onChange={(e) => setCapacity(e.target.value)} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!name || !capacity || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Hostel'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
