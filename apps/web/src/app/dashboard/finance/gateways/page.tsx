'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CreditCard, Check, X, ExternalLink, ShieldCheck, Eye, EyeOff,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const GATEWAYS = [
  { key: 'PAYSTACK', name: 'Paystack', logo: '🟢', fields: ['publicKey', 'secretKey'], region: 'Nigeria, Ghana, South Africa' },
  { key: 'FLUTTERWAVE', name: 'Flutterwave', logo: '🟠', fields: ['publicKey', 'secretKey'], region: 'Africa-wide' },
  { key: 'STRIPE', name: 'Stripe', logo: '🟣', fields: ['publicKey', 'secretKey', 'webhookSecret'], region: 'Global' },
  { key: 'MONNIFY', name: 'Monnify', logo: '🔵', fields: ['apiKey', 'secretKey', 'contractCode'], region: 'Nigeria' },
  { key: 'INTERSWITCH', name: 'Interswitch', logo: '🟡', fields: ['clientId', 'clientSecret'], region: 'Nigeria' },
  { key: 'PAYPAL', name: 'PayPal', logo: '🔷', fields: ['clientId', 'clientSecret'], region: 'Global' },
  { key: 'SQUARE', name: 'Square', logo: '⬛', fields: ['accessToken', 'locationId'], region: 'US, Canada, UK' },
  { key: 'RAZORPAY', name: 'Razorpay', logo: '🔵', fields: ['keyId', 'keySecret'], region: 'India' },
];

export default function GatewaysPage() {
  const [configOpen, setConfigOpen] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data: configs } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => api.get<any>('/v1/finance/gateways'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ gateway, data }: { gateway: string; data: any }) =>
      api.put(`/v1/finance/gateways/${gateway}`, data),
    onSuccess: () => {
      toast.success('Gateway configuration saved');
      qc.invalidateQueries({ queryKey: ['gateways'] });
      setConfigOpen(null);
      setFormData({});
    },
    onError: () => toast.error('Failed to save configuration'),
  });

  const toggleEnabled = (gateway: string, isEnabled: boolean, current: any) => {
    updateMutation.mutate({
      gateway,
      data: { isEnabled, isLive: current?.isLive ?? false, displayName: current?.displayName, config: current?.config ?? {} },
    });
  };

  const getConfig = (key: string) => (configs || []).find((c: any) => c.gateway === key);

  const openConfig = (key: string) => {
    const existing = getConfig(key);
    setIsLive(existing?.isLive ?? false);
    setFormData({});
    setConfigOpen(key);
  };

  const saveConfig = () => {
    if (!configOpen) return;
    updateMutation.mutate({
      gateway: configOpen,
      data: { isEnabled: getConfig(configOpen)?.isEnabled ?? false, isLive, config: formData },
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Payment Gateways</h1>
          <p className="section-subtitle">Configure payment methods available to parents and students</p>
        </div>
        <Badge variant="secondary" className="gap-1.5 py-1.5 px-3">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          Encrypted Storage
        </Badge>
      </div>

      {/* Always available */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Manual Payment Methods</CardTitle>
          <CardDescription>Always available, no configuration required</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { name: 'Cash', icon: '💵' },
              { name: 'Bank Transfer', icon: '🏦' },
              { name: 'Manual / Cheque', icon: '📝' },
            ].map((m) => (
              <div key={m.name} className="flex items-center gap-3 border rounded-lg p-3">
                <span className="text-2xl">{m.icon}</span>
                <div className="flex-1">
                  <p className="font-medium text-sm">{m.name}</p>
                  <Badge variant="secondary" className="badge-success text-xs">Always Active</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Configurable gateways */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Online Payment Gateways</CardTitle>
          <CardDescription>Enable and configure third-party payment providers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {GATEWAYS.map((gw) => {
              const config = getConfig(gw.key);
              const isEnabled = config?.isEnabled ?? false;
              const isConfigured = config?.config && Object.keys(config.config).length > 0;

              return (
                <div key={gw.key} className="flex items-center gap-4 border rounded-lg p-4 hover:bg-muted/30 transition-colors">
                  <span className="text-3xl">{gw.logo}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm">{gw.name}</p>
                      {config?.isLive ? (
                        <Badge variant="secondary" className="badge-success text-xs">Live</Badge>
                      ) : (
                        <Badge variant="secondary" className="badge-warning text-xs">Test Mode</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{gw.region}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => openConfig(gw.key)} disabled={!hasPermission('finance:gateways:MANAGE')}>
                    Configure
                  </Button>
                  <Switch
                    checked={isEnabled}
                    disabled={!isConfigured && !isEnabled}
                    onCheckedChange={(v) => toggleEnabled(gw.key, v, config)}
                  />
                </div>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Only enabled gateways with valid configuration will appear to parents during checkout. API keys are encrypted at rest.
          </p>
        </CardContent>
      </Card>

      {/* Config Dialog */}
      <Dialog open={!!configOpen} onOpenChange={() => setConfigOpen(null)}>
        <DialogContent className="max-w-md">
          {configOpen && (() => {
            const gw = GATEWAYS.find((g) => g.key === configOpen)!;
            return (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <span className="text-2xl">{gw.logo}</span> Configure {gw.name}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="flex items-center justify-between bg-muted/50 rounded-lg p-3">
                    <div>
                      <p className="text-sm font-medium">Live Mode</p>
                      <p className="text-xs text-muted-foreground">Toggle off for test/sandbox credentials</p>
                    </div>
                    <Switch checked={isLive} onCheckedChange={setIsLive} />
                  </div>

                  {gw.fields.map((field) => (
                    <div key={field} className="space-y-1.5">
                      <Label className="capitalize">{field.replace(/([A-Z])/g, ' $1')}</Label>
                      <div className="relative">
                        <Input
                          type={showSecrets ? 'text' : 'password'}
                          value={formData[field] || ''}
                          onChange={(e) => setFormData((p) => ({ ...p, [field]: e.target.value }))}
                          placeholder={`Enter ${gw.name} ${field}`}
                          className="pr-10"
                        />
                        <button
                          type="button"
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                          onClick={() => setShowSecrets((p) => !p)}
                        >
                          {showSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  ))}

                  <p className="text-xs text-muted-foreground">
                    Find these credentials in your {gw.name} dashboard under API/Developer settings.
                  </p>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setConfigOpen(null)}>Cancel</Button>
                  <Button onClick={saveConfig} disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? 'Saving...' : 'Save Configuration'}
                  </Button>
                </DialogFooter>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>
    </div>
  );
}
