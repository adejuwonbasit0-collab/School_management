'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { Eye, EyeOff, GraduationCap, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/store/auth.store';
import { apiClient } from '@/lib/api-client';
import toast from 'react-hot-toast';
import Link from 'next/link';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
  mfaToken: z.string().optional(),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [requiresMfa, setRequiresMfa] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { setTokens, setUser } = useAuthStore();
  const router = useRouter();

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', mfaToken: '' },
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      const res = await apiClient.post('/v1/auth/login', data);
      const result = res.data.data;

      if (result.requiresMfa) {
        setRequiresMfa(true);
        toast('Enter your 2FA code to continue');
        return;
      }

      setTokens(result.tokens.accessToken, result.tokens.refreshToken);
      setUser(result.user);
      toast.success(`Welcome back, ${result.user.firstName}!`);
      router.push('/dashboard');
    } catch (err: any) {
      const message = err.response?.data?.message || 'Login failed';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)',
          backgroundSize: '32px 32px',
        }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md relative"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4 shadow-lg shadow-blue-600/30">
            <GraduationCap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">EduCore</h1>
          <p className="text-blue-300/70 text-sm mt-1">Enterprise School Management</p>
        </div>

        <Card className="border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-white text-xl">
              {requiresMfa ? 'Two-Factor Authentication' : 'Sign In'}
            </CardTitle>
            <CardDescription className="text-blue-300/70">
              {requiresMfa
                ? 'Enter your 6-digit authenticator code'
                : 'Enter your credentials to access the platform'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {!requiresMfa ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-white/80 text-sm">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="admin@school.edu.ng"
                      {...form.register('email')}
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/30 focus:border-blue-400"
                    />
                    {form.formState.errors.email && (
                      <p className="text-red-400 text-xs">{form.formState.errors.email.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-white/80 text-sm">Password</Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        {...form.register('password')}
                        className="bg-white/10 border-white/20 text-white placeholder:text-white/30 focus:border-blue-400 pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((p) => !p)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {form.formState.errors.password && (
                      <p className="text-red-400 text-xs">{form.formState.errors.password.message}</p>
                    )}
                  </div>

                  <div className="flex justify-end">
                    <Link href="/auth/forgot-password" className="text-xs text-blue-400 hover:text-blue-300">
                      Forgot password?
                    </Link>
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="mfaToken" className="text-white/80 text-sm">Authenticator Code</Label>
                  <Input
                    id="mfaToken"
                    type="text"
                    placeholder="000000"
                    maxLength={8}
                    {...form.register('mfaToken')}
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/30 focus:border-blue-400 text-center text-2xl tracking-widest"
                    autoFocus
                  />
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white h-10 font-medium"
              >
                {isLoading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Signing in...</>
                ) : requiresMfa ? 'Verify Code' : 'Sign In'}
              </Button>

              {requiresMfa && (
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full text-white/50 hover:text-white/80"
                  onClick={() => setRequiresMfa(false)}
                >
                  Back to login
                </Button>
              )}
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-blue-300/40 text-xs mt-6">
          © {new Date().getFullYear()} EduCore Platform. Enterprise Edition.
        </p>
      </motion.div>
    </div>
  );
}
