'use client';
import { Suspense, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { GraduationCap, Loader2, Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import toast from 'react-hot-toast';
import Link from 'next/link';

const schema = z.object({
  password: z.string().min(8).regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/, 'Must contain uppercase, lowercase, number and special char'),
  confirmPassword: z.string(),
}).refine((d) => d.password === d.confirmPassword, { message: 'Passwords do not match', path: ['confirmPassword'] });

function ResetPasswordContent() {
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [show, setShow] = useState(false);
  const params = useSearchParams();
  const router = useRouter();
  const form = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (data: any) => {
    const token = params.get('token');
    if (!token) { toast.error('Invalid reset link'); return; }
    setLoading(true);
    try {
      await apiClient.post('/v1/auth/reset-password', { token, password: data.password });
      setDone(true);
      setTimeout(() => router.push('/auth/login'), 2000);
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Reset failed. Link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4"><GraduationCap className="w-7 h-7 text-white" /></div>
          <h1 className="text-2xl font-bold text-white">EduCore</h1>
        </div>
        <Card className="border-white/10 bg-white/5 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white">{done ? 'Password Reset!' : 'New Password'}</CardTitle>
            <CardDescription className="text-blue-300/70">{done ? 'Redirecting to login...' : 'Choose a strong new password.'}</CardDescription>
          </CardHeader>
          <CardContent>
            {done ? (
              <div className="text-center py-4"><CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" /><p className="text-white/80">Your password has been updated.</p></div>
            ) : (
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-white/80">New Password</Label>
                  <div className="relative">
                    <Input {...form.register('password')} type={show ? 'text' : 'password'} className="bg-white/10 border-white/20 text-white pr-10" />
                    <button type="button" onClick={() => setShow((p) => !p)} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40">
                      {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {form.formState.errors.password && <p className="text-red-400 text-xs">{String(form.formState.errors.password.message)}</p>}
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Confirm Password</Label>
                  <Input {...form.register('confirmPassword')} type={show ? 'text' : 'password'} className="bg-white/10 border-white/20 text-white" />
                  {form.formState.errors.confirmPassword && <p className="text-red-400 text-xs">{String(form.formState.errors.confirmPassword.message)}</p>}
                </div>
                <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-500">
                  {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Resetting...</> : 'Reset Password'}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordContent />
    </Suspense>
  );
}
