'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { AuthLayout, SocialLogin } from '@/components/auth';
import { loginSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';

import { useAuth } from '@/hooks/useAuth';

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // 2FA State
  const [show2FA, setShow2FA] = useState(false);
  const [preAuthToken, setPreAuthToken] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [twoFaError, setTwoFaError] = useState('');

  const { login } = useAuth(); // If we use context, we assume context logic might need update too,
  // but here we are doing manual fetch first.
  // Ideally useAuth should handle this, but for speed modifying Page first.

  const handleLoginSubmit = async (data: LoginFormData, methods: UseFormReturn<LoginFormData>) => {
    setIsLoggingIn(true);
    try {
      const formData = new URLSearchParams();
      // loginSchema uses 'identifier'
      formData.append('username', data.identifier);
      formData.append('password', data.password);

      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (response.status === 202) {
        // 2FA Required
        const result = await response.json();
        setPreAuthToken(result.pre_auth_token);
        setShow2FA(true);
        return; // Stop here, wait for OTP
      }

      if (!response.ok) {
        const errorData = await response.json();
        const code = errorData.detail?.code;

        // Map login-specific error codes
        if (code === 'AUTH001') {
          methods.setError('identifier', { message: 'Invalid username/email or password' });
          return;
        }

        const errorMessage = errorData.detail?.message || errorData.detail || 'Login failed';
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log('Login successful:', result);
      // Store token (Basic implementation) - useAuth should handle this
      localStorage.setItem('token', result.access_token);
      router.push('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      methods.setError('root', {
        message: error instanceof Error ? error.message : 'Invalid credentials',
      });
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleVerifyOTP = async () => {
    setIsLoggingIn(true);
    setTwoFaError('');
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login/2fa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pre_auth_token: preAuthToken,
          code: otpCode,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail?.message || 'Verification failed');
      }

      const result = await response.json();
      localStorage.setItem('token', result.access_token);
      window.location.href = '/dashboard';
    } catch (error) {
      setTwoFaError(error instanceof Error ? error.message : 'Invalid Code');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const isLoading = isLoggingIn; // Alias for the UI

  if (show2FA) {
    return (
      <AuthLayout title="Two-Factor Authentication" subtitle="Enter the code sent to your email">
        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              Verification Code
            </label>
            <Input
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
              placeholder="123456"
              className="text-center text-lg tracking-widest"
              maxLength={6}
              disabled={isLoading}
            />
            {twoFaError && (
              <p className="text-sm font-medium text-destructive text-red-500">{twoFaError}</p>
            )}
          </div>

          <Button
            onClick={handleVerifyOTP}
            className="w-full"
            disabled={isLoading || otpCode.length !== 6}
          >
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : 'Verify Code'}
          </Button>

          <Button
            variant="ghost"
            onClick={() => setShow2FA(false)}
            className="w-full text-muted-foreground"
            disabled={isLoading}
          >
            Back to Login
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Enter your credentials to access your account">
      <Form
        schema={loginSchema}
        onSubmit={handleLoginSubmit}
        className={`space-y-5 transition-opacity duration-200 ${isLoading ? 'opacity-60 pointer-events-none' : ''}`}
      >
        {(methods) => (
          <>
            {methods.formState.errors.root && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs p-3 rounded-md flex items-center mb-5">
                <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                {methods.formState.errors.root.message}
              </div>
            )}
            <FormKeyboardListener reset={methods.reset} />
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <FormField
                control={methods.control}
                name="identifier"
                label="Email or Username"
                placeholder="you@example.com or username"
                type="text"
                required
                disabled={isLoading}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 }}
            >
              <FormField control={methods.control} name="password" label="Password" required>
                {(fieldProps) => (
                  <div className="relative">
                    <Input
                      {...fieldProps}
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      className="pr-10"
                      disabled={isLoading}
                      // SECURITY HARDENING START
                      autoComplete="off"
                      onPaste={(e) => {
                        e.preventDefault();
                        return false;
                      }}
                      onCopy={(e) => {
                        e.preventDefault();
                        return false;
                      }}
                      onCut={(e) => {
                        e.preventDefault();
                        return false;
                      }}
                      onContextMenu={(e) => {
                        e.preventDefault();
                        return false;
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                )}
              </FormField>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="flex items-center justify-between"
            >
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  {...methods.register('rememberMe')}
                  disabled={isLoading}
                  className="h-4 w-4 rounded border-input text-brand-primary focus:ring-brand-primary transition-colors cursor-pointer disabled:cursor-not-allowed"
                />
                <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                  Remember me
                </span>
              </label>
              <Link
                href="/forgot-password"
                className="text-sm text-primary hover:text-primary/80 transition-colors"
              >
                Forgot password?
              </Link>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-11 bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <SocialLogin isLoading={isLoading} />
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45 }}
              className="text-center text-sm text-muted-foreground"
            >
              Don&apos;t have an account?{' '}
              <Link
                href="/register"
                className="text-primary hover:text-primary/80 font-medium transition-colors"
              >
                Sign up
              </Link>
            </motion.p>
          </>
        )}
      </Form>
    </AuthLayout>
  );
}

function FormKeyboardListener({ reset }: { reset: (values?: any) => void }) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        // Clear all fields to empty strings
        reset({
          identifier: '',
          password: '',
          rememberMe: false,
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [reset]);

  return null;
}
