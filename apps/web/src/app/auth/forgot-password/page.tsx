'use client';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { GraduationCap, Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import toast from 'react-hot-toast';
import Link from 'next/link';

const schema = z.object({ email: z.string().email('Enter a valid email') });

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const form = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      await apiClient.post('/v1/auth/forgot-password', data);
      setSent(true);
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to send reset link');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4 shadow-lg shadow-blue-600/30">
            <GraduationCap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">EduCore</h1>
        </div>
        <Card className="border-white/10 bg-white/5 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white">{sent ? 'Check Your Email' : 'Reset Password'}</CardTitle>
            <CardDescription className="text-blue-300/70">
              {sent ? 'We sent a reset link to your email address.' : 'Enter your email to receive a password reset link.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sent ? (
              <div className="text-center py-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                <p className="text-white/80 text-sm">Check your inbox and click the reset link. The link expires in 1 hour.</p>
              </div>
            ) : (
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-white/80">Email Address</Label>
                  <Input {...form.register('email')} type="email" placeholder="you@school.edu.ng" className="bg-white/10 border-white/20 text-white placeholder:text-white/30" />
                  {form.formState.errors.email && <p className="text-red-400 text-xs">{String(form.formState.errors.email.message)}</p>}
                </div>
                <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-500">
                  {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Sending...</> : 'Send Reset Link'}
                </Button>
              </form>
            )}
            <Link href="/auth/login" className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-sm mt-4 justify-center">
              <ArrowLeft className="w-3.5 h-3.5" />Back to login
            </Link>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
