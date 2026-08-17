'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Zap, Plus, Play, Pause, Trash2, ArrowRight, Bell, Mail,
  MessageSquare, Webhook, CheckCircle2, AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

const TRIGGER_OPTIONS = [
  { value: 'STUDENT_ENROLLED', label: 'Student Enrolled', icon: '🎓' },
  { value: 'FEE_PAID', label: 'Fee Payment Received', icon: '💰' },
  { value: 'ATTENDANCE_MARKED', label: 'Attendance Marked', icon: '✅' },
  { value: 'RESULT_PUBLISHED', label: 'Exam Result Published', icon: '📊' },
  { value: 'ADMISSION_STATUS_CHANGED', label: 'Admission Status Changed', icon: '📋' },
  { value: 'LEAVE_APPROVED', label: 'Leave Approved', icon: '🗓️' },
  { value: 'ASSIGNMENT_SUBMITTED', label: 'Assignment Submitted', icon: '📝' },
  { value: 'EXAM_SCHEDULED', label: 'Exam Scheduled', icon: '📅' },
  { value: 'BIRTHDAY', label: 'Student/Staff Birthday', icon: '🎂' },
];

const ACTION_OPTIONS = [
  { value: 'SEND_EMAIL', label: 'Send Email', icon: Mail },
  { value: 'SEND_SMS', label: 'Send SMS', icon: MessageSquare },
  { value: 'CREATE_NOTIFICATION', label: 'In-App Notification', icon: Bell },
  { value: 'WEBHOOK', label: 'Call Webhook', icon: Webhook },
];

const TEMPLATES = [
  { name: 'Absent Student → Notify Parent', trigger: 'ATTENDANCE_MARKED', action: 'SEND_EMAIL', desc: 'Automatically email parents when their child is marked absent' },
  { name: 'Fee Paid → Send Receipt', trigger: 'FEE_PAID', action: 'SEND_EMAIL', desc: 'Send a payment receipt automatically when fees are paid' },
  { name: 'Admission Approved → Welcome Email', trigger: 'ADMISSION_STATUS_CHANGED', action: 'SEND_EMAIL', desc: 'Send welcome email when a student is admitted' },
  { name: 'Result Published → Notify Parent', trigger: 'RESULT_PUBLISHED', action: 'SEND_EMAIL', desc: 'Notify parents when exam results are published' },
];

export default function AutomationPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [trigger, setTrigger] = useState('');
  const [actionType, setActionType] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data: automations, isLoading } = useQuery({
    queryKey: ['automations'],
    queryFn: () => api.get<any>('/v1/automation'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post('/v1/automation', {
      name, description, trigger,
      actions: [{ type: actionType, config: { subject: emailSubject, body: emailBody } }],
      isActive: true,
    }),
    onSuccess: () => {
      toast.success('Automation created');
      qc.invalidateQueries({ queryKey: ['automations'] });
      setCreateOpen(false);
      setName(''); setDescription(''); setTrigger(''); setActionType(''); setEmailSubject(''); setEmailBody('');
    },
    onError: (err: any) => toast.error(err.response?.data?.message || 'Failed'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      api.put(`/v1/automation/${id}`, { isActive }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['automations'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/automation/${id}`),
    onSuccess: () => { toast.success('Automation deleted'); qc.invalidateQueries({ queryKey: ['automations'] }); },
  });

  const list = automations || [];

  const applyTemplate = (tpl: typeof TEMPLATES[0]) => {
    setName(tpl.name);
    setDescription(tpl.desc);
    setTrigger(tpl.trigger);
    setActionType(tpl.action);
    setCreateOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Automation Center</h1>
          <p className="section-subtitle">Build workflows that run automatically based on triggers</p>
        </div>
        {hasPermission('automation:automation:CREATE') && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />New Automation
          </Button>
        )}
      </div>

      {/* Templates */}
      {list.length === 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Quick Start Templates</CardTitle>
            <CardDescription>Get started with these common automation workflows</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {TEMPLATES.map((tpl) => (
                <button
                  key={tpl.name}
                  onClick={() => applyTemplate(tpl)}
                  className="text-left border rounded-lg p-4 hover:border-primary/50 hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Zap className="w-4 h-4 text-primary" />
                    <p className="font-medium text-sm">{tpl.name}</p>
                  </div>
                  <p className="text-xs text-muted-foreground">{tpl.desc}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Automations */}
      <div className="space-y-3">
        {list.map((auto: any) => {
          const triggerCfg = TRIGGER_OPTIONS.find((t) => t.value === auto.trigger);
          const actions = (auto.actions || []) as any[];
          return (
            <Card key={auto.id} className="shadow-card">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-sm">{auto.name}</h3>
                      <Badge variant="secondary" className={auto.isActive ? 'badge-success text-xs' : 'badge-neutral text-xs'}>
                        {auto.isActive ? 'Active' : 'Paused'}
                      </Badge>
                    </div>
                    {auto.description && <p className="text-xs text-muted-foreground mb-3">{auto.description}</p>}

                    {/* Flow visualization */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400 rounded-lg px-3 py-1.5 text-xs font-medium">
                        <span>{triggerCfg?.icon}</span>
                        {triggerCfg?.label || auto.trigger}
                      </div>
                      <ArrowRight className="w-4 h-4 text-muted-foreground" />
                      {actions.map((action, i) => {
                        const actionCfg = ACTION_OPTIONS.find((a) => a.value === action.type);
                        const Icon = actionCfg?.icon || Zap;
                        return (
                          <div key={i} className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 rounded-lg px-3 py-1.5 text-xs font-medium">
                            <Icon className="w-3.5 h-3.5" />
                            {actionCfg?.label || action.type}
                          </div>
                        );
                      })}
                    </div>

                    <div className="flex gap-4 mt-3 text-xs text-muted-foreground">
                      <span>Ran {auto.runCount} times</span>
                      {auto.lastRunAt && <span>Last run: {new Date(auto.lastRunAt).toLocaleDateString()}</span>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Switch
                      checked={auto.isActive}
                      onCheckedChange={(v) => toggleMutation.mutate({ id: auto.id, isActive: v })}
                    />
                    <Button
                      variant="ghost" size="icon" className="w-8 h-8 text-destructive"
                      onClick={() => { if (confirm('Delete this automation?')) deleteMutation.mutate(auto.id); }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Zap className="w-5 h-5 text-primary" />Create Automation</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Name *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Notify parents on absence" />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>

            <div className="space-y-1.5">
              <Label>When this happens (Trigger) *</Label>
              <Select value={trigger} onValueChange={setTrigger}>
                <SelectTrigger><SelectValue placeholder="Select trigger event" /></SelectTrigger>
                <SelectContent>
                  {TRIGGER_OPTIONS.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.icon} {t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex justify-center">
              <ArrowRight className="w-5 h-5 text-muted-foreground rotate-90" />
            </div>

            <div className="space-y-1.5">
              <Label>Do this (Action) *</Label>
              <Select value={actionType} onValueChange={setActionType}>
                <SelectTrigger><SelectValue placeholder="Select action" /></SelectTrigger>
                <SelectContent>
                  {ACTION_OPTIONS.map((a) => (
                    <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {(actionType === 'SEND_EMAIL' || actionType === 'SEND_SMS') && (
              <>
                {actionType === 'SEND_EMAIL' && (
                  <div className="space-y-1.5">
                    <Label>Email Subject</Label>
                    <Input value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} placeholder="Notification from {{schoolName}}" />
                  </div>
                )}
                <div className="space-y-1.5">
                  <Label>Message Body</Label>
                  <Textarea
                    value={emailBody}
                    onChange={(e) => setEmailBody(e.target.value)}
                    rows={3}
                    placeholder="Use variables like {{studentName}}, {{date}}, {{amount}}"
                  />
                  <p className="text-xs text-muted-foreground">
                    Available variables depend on trigger: studentName, parentName, date, amount, etc.
                  </p>
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={!name || !trigger || !actionType || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Automation'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
