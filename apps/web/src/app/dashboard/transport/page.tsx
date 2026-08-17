'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bus, Plus, MapPin, Users, Phone, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

export default function TransportPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [fee, setFee] = useState('');
  const [vehicle, setVehicle] = useState('');
  const [driver, setDriver] = useState('');
  const [driverPhone, setDriverPhone] = useState('');
  const { hasPermission, user } = useAuth();
  const sym = user?.school?.currencySymbol || '₦';
  const qc = useQueryClient();

  const { data: routes, isLoading } = useQuery({
    queryKey: ['transport-routes'],
    queryFn: () => api.get<any>('/v1/transport/routes'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/transport/routes', {
      name, description, fee: fee ? Number(fee) : undefined, vehicle, driver, driverPhone, stops: [],
    }),
    onSuccess: () => {
      toast.success('Route created');
      qc.invalidateQueries({ queryKey: ['transport-routes'] });
      setCreateOpen(false);
      setName(''); setDescription(''); setFee(''); setVehicle(''); setDriver(''); setDriverPhone('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const list = routes || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Transport</h1>
          <p className="section-subtitle">Manage school bus routes and assignments</p>
        </div>
        {hasPermission('transport:transport:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />New Route
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.length === 0 && !isLoading && (
          <Card className="col-span-full">
            <CardContent className="py-16 text-center text-muted-foreground">
              <Bus className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>No transport routes created yet</p>
            </CardContent>
          </Card>
        )}
        {list.map((route: any) => (
          <Card key={route.id} className="shadow-card">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                  <Bus className="w-5 h-5 text-blue-600" />
                </div>
                <Badge variant="secondary" className={route.status === 'ACTIVE' ? 'badge-success' : 'badge-neutral'}>
                  {route.status}
                </Badge>
              </div>
              <h3 className="font-semibold">{route.name}</h3>
              {route.description && <p className="text-xs text-muted-foreground mt-0.5">{route.description}</p>}

              <div className="space-y-1.5 mt-3 text-sm">
                {route.vehicle && <div className="flex items-center gap-2 text-muted-foreground"><Bus className="w-3.5 h-3.5" />{route.vehicle}</div>}
                {route.driver && <div className="flex items-center gap-2 text-muted-foreground"><Users className="w-3.5 h-3.5" />{route.driver}</div>}
                {route.driverPhone && <div className="flex items-center gap-2 text-muted-foreground"><Phone className="w-3.5 h-3.5" />{route.driverPhone}</div>}
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t">
                <span className="text-sm font-semibold">{route.fee ? `${sym}${Number(route.fee).toLocaleString()}/term` : 'No fee'}</span>
                <span className="text-xs text-muted-foreground">{route._count?.students || 0} students</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>New Transport Route</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Route Name *</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Route A - Ikeja" /></div>
            <div className="space-y-1.5"><Label>Description</Label><Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Vehicle</Label><Input value={vehicle} onChange={(e) => setVehicle(e.target.value)} placeholder="Bus 01 - ABC123XY" /></div>
              <div className="space-y-1.5"><Label>Fee per Term ({sym})</Label><Input type="number" value={fee} onChange={(e) => setFee(e.target.value)} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Driver Name</Label><Input value={driver} onChange={(e) => setDriver(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Driver Phone</Label><Input value={driverPhone} onChange={(e) => setDriverPhone(e.target.value)} /></div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!name || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Route'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
