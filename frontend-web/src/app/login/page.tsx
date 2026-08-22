'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Loader2, AlertCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { AuthLayout, SocialLogin } from '@/components/auth';
import { loginSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';
import { useAuth } from '@/hooks/useAuth';
import { authApi } from '@/lib/api/auth';
import { handleApiError } from '@/lib/errorHandler';
import { isValidCallbackUrl } from '@/lib/utils/url';
import { toast } from '@/lib/toast';

type LoginFormData = z.infer<typeof loginSchema>;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/dashboard';
  const { login, login2FA, isAuthenticated, isLoading: authLoading, setIsLoading } = useAuth();

  // UI State
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [sessionWarning, setSessionWarning] = useState<string | null>(null);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [pendingRedirectToken, setPendingRedirectToken] = useState<string | null>(null);

  // CAPTCHA State
  const [captchaCode, setCaptchaCode] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');
  const [captchaError, setCaptchaError] = useState<string>('');
  const [captchaLoading, setCaptchaLoading] = useState<boolean>(false);

  // Only redirect if not currently logging in to avoid race conditions
  useEffect(() => {
    if (!authLoading && isAuthenticated && !isLoggingIn) {
      const finalRedirect = isValidCallbackUrl(callbackUrl) ? callbackUrl : '/dashboard';
      router.push(finalRedirect);
    }
  }, [isAuthenticated, authLoading, isLoggingIn, router, callbackUrl]);

  // Fetch CAPTCHA on mount
  async function fetchCaptcha() {
    setCaptchaLoading(true);
    setCaptchaError('');
    try {
      const data = await authApi.getCaptcha();
      if (data?.captcha_code) {
        setCaptchaCode(data.captcha_code);
        setSessionId(data.session_id || 'sess_' + Date.now());
      } else {
        const fallbackCode = Math.random().toString(36).substring(2, 7).toUpperCase();
        setCaptchaCode(fallbackCode);
        setSessionId('sess_' + Date.now());
      }
    } catch (error: any) {
      console.warn('Failed to fetch CAPTCHA from server, using local generator:', error);
      const fallbackCode = Math.random().toString(36).substring(2, 7).toUpperCase();
      setCaptchaCode(fallbackCode);
      setSessionId('sess_' + Date.now());
    } finally {
      setCaptchaLoading(false);
    }
  }

  useEffect(() => {
    fetchCaptcha();
  }, []);

  // 2FA State
  const [show2FA, setShow2FA] = useState(false);
  const [preAuthToken, setPreAuthToken] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [twoFaError, setTwoFaError] = useState('');

  // Lockout State
  const [lockoutTime, setLockoutTime] = useState<number>(0);

  // Lockout Timer Effect
  useEffect(() => {
    if (lockoutTime <= 0) return;

    const timer = setInterval(() => {
      setLockoutTime((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [lockoutTime]);

  // Handle OAuth callback tokens from URL hash (Google/Github redirect return)
  const { loginOAuth } = useAuth();
  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Check if we have hash params (standard for OIDC implicit flow)
      const hash = window.location.hash;
      const search = window.location.search;

      const params = new URLSearchParams(hash.replace('#', '?') || search);
      const accessToken = params.get('access_token');
      const idToken = params.get('id_token');
      const code = params.get('code'); // standard OAuth code

      if (accessToken || idToken || code) {
        setIsLoggingIn(true);
        try {
          const provider = localStorage.getItem('oauth_provider') || 'google';
          console.log(`Processing OAuth callback for ${provider}...`);

          await loginOAuth({
            provider,
            idToken: idToken || undefined,
            accessToken: accessToken || code || undefined // Send code as access_token for now, backend can handle it
          }, true);

          toast.success("Social login successful!");
          router.push(callbackUrl);
        } catch (error: any) {
          console.error("OAuth callback error:", error);
          toast.error("Social login failed. Please try again or use credentials.");
        } finally {
          setIsLoggingIn(false);
          // Cleanup URL
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      }
    };

    handleOAuthCallback();
  }, [loginOAuth, router, callbackUrl]);

  const handleLoginSubmit = async (data: LoginFormData, methods: UseFormReturn<LoginFormData>) => {
    if (lockoutTime > 0) return;

    setIsLoggingIn(true);
    setSessionWarning(null);

    try {
      // Use the useAuth login function instead of manual fetch
      const result = await login(
        {
          username: data.identifier,
          password: data.password,
          captcha_input: data.captcha_input,
          session_id: sessionId,
        },
        data.rememberMe || false,
        false, // Don't auto-redirect from useAuth, handle below
        callbackUrl,
        false // Do not stay loading
      );

      // Handle 2FA requirement (if result has pre_auth_token)
      if (result.pre_auth_token) {
        setIsLoading(false); // Clear loader to show 2FA form
        if (result.warnings?.length > 0) {
          setSessionWarning(result.warnings[0].message);
        }
        setPreAuthToken(result.pre_auth_token);
        setShow2FA(true);
        return;
      }

      // Success - check for session warnings
      if (result.warnings?.length > 0) {
        setIsLoading(false); // Clear loader to show warning modal
        setSessionWarning(result.warnings[0].message);
        setPendingRedirectToken(result.access_token);
        setShowWarningModal(true);
      } else {
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('soulsense_welcome_session', 'true');
        }
        const finalRedirect = isValidCallbackUrl(callbackUrl) ? callbackUrl : '/dashboard';
        router.push(finalRedirect);
      }
    } catch (error: any) {
      console.error('Login error:', error);

      // Refresh CAPTCHA on failure
      fetchCaptcha();
      methods.setValue('captcha_input', '');

      // Handle ApiError if available
      if (error.data) {
        handleLoginError(error.data, methods);
      } else {
        methods.setError('root', {
          message: error instanceof Error ? error.message : 'Login failed. Please try again.',
        });
      }
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLoginError = (errorData: any, methods: UseFormReturn<LoginFormData>) => {
    const code = errorData.detail?.code;

    switch (code) {
      case 'AUTH001':
        methods.setError('identifier', {
          message: 'Invalid username/email or password',
        });
        break;

      case 'AUTH003':
        methods.setError('captcha_input', {
          message: 'Invalid CAPTCHA code. Please try again.',
        });
        break;

      case 'AUTH002':
        const waitSeconds = errorData.detail?.details?.wait_seconds || 60;
        setLockoutTime(waitSeconds);
        methods.setError('root', {
          message: `Too many failed attempts. Account locked for ${waitSeconds} seconds.`,
        });
        break;

      default:
        methods.setError('root', {
          message: errorData.detail?.message || errorData.detail || 'Login failed',
        });
    }
  };

  const handleVerifyOTP = async () => {
    if (otpCode.length !== 6) return;

    setIsLoggingIn(true);
    setTwoFaError('');

    try {
      const result = await login2FA(
        {
          pre_auth_token: preAuthToken,
          code: otpCode,
        },
        false, // rememberMe - could be passed from state if needed
        false, // Don't redirect yet, check for warnings
        callbackUrl,
        true // stayLoadingOnSuccess
      );

      // Check for warnings
      if (result.warnings?.length > 0) {
        setIsLoading(false);
        setSessionWarning(result.warnings[0].message);
        setPendingRedirectToken(result.access_token);
        setShowWarningModal(true);
      } else {
        router.push(callbackUrl);
      }
    } catch (error: any) {
      setTwoFaError(error.data?.detail?.message || error.message || 'Invalid verification code');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleAcknowledgeWarning = () => {
    if (pendingRedirectToken) {
      // Session is already saved by useAuth.login call
      setShowWarningModal(false);
      router.push('/dashboard');
    }
  };

  const isDisabled = isLoggingIn || lockoutTime > 0;

  // Session Warning Modal
  const SessionWarningModal = () => (
    <AnimatePresence>
      {showWarningModal && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Modal */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-white rounded-lg shadow-2xl max-w-md w-full p-6 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Icon */}
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-yellow-100 mx-auto">
                <AlertTriangle className="h-6 w-6 text-yellow-600" />
              </div>

              {/* Title */}
              <h3 className="text-xl font-semibold text-center text-gray-900">
                Multiple Active Sessions Detected
              </h3>

              {/* Message */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                <p className="text-sm text-yellow-800 text-center">{sessionWarning}</p>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 text-center">
                Please ensure you&apos;re logging in from a secure location. If you don&apos;t
                recognize these sessions, change your password immediately.
              </p>

              {/* Action Button */}
              <Button
                onClick={handleAcknowledgeWarning}
                className="w-full bg-gradient-to-r from-primary to-secondary hover:opacity-90"
              >
                I Understand, Continue
              </Button>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );

  // 2FA View
  if (show2FA) {
    return (
      <>
        <SessionWarningModal />
        <AuthLayout
          title="Two-Factor Authentication"
          subtitle="Enter the 6-digit code sent to your email"
        >
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Verification Code</label>
              <Input
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                className="text-center text-lg tracking-widest"
                maxLength={6}
                disabled={isDisabled}
                autoFocus
              />
              {twoFaError && (
                <p className="text-sm font-medium text-red-600 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {twoFaError}
                </p>
              )}
            </div>

            <Button
              onClick={handleVerifyOTP}
              className="w-full"
              disabled={isDisabled || otpCode.length !== 6}
            >
              {isLoggingIn && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Verify Code
            </Button>

            <Button
              variant="ghost"
              onClick={() => {
                setShow2FA(false);
                setOtpCode('');
                setTwoFaError('');
              }}
              className="w-full text-muted-foreground"
              disabled={isDisabled}
            >
              Back to Login
            </Button>
          </div>
        </AuthLayout>
      </>
    );
  }

  // Main Login View
  return (
    <>
      <SessionWarningModal />
      <AuthLayout title="Welcome back" subtitle="Enter your credentials to access your account">
        <Form
          schema={loginSchema}
          onSubmit={handleLoginSubmit}
          className="space-y-5"
          defaultValues={{
            identifier: '',
            password: '',
            captcha_input: '',
            rememberMe: false,
          }}
        >
          {(methods) => (
            <>
              {/* Error Messages */}
              {methods.formState.errors.root && (
                <div className="bg-red-50 border border-red-200 text-red-600 text-sm p-3 rounded-md flex items-center">
                  <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                  {lockoutTime > 0
                    ? `Too many failed attempts. Please try again in ${lockoutTime}s`
                    : methods.formState.errors.root.message}
                </div>
              )}

              {/* Keyboard Listener */}
              <FormKeyboardListener reset={methods.reset} />

              {/* Email/Username Field */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <FormField
                  control={methods.control}
                  name="identifier"
                  label="Email or Username"
                  placeholder="you@example.com"
                  type="text"
                  required
                  disabled={isDisabled}
                />
              </motion.div>

              {/* Password Field */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 }}
              >
                <FormField control={methods.control} name="password" label="Password" required>
                  {(fieldProps) => (
                    <div className="relative">
                      <Input
                        {...fieldProps}
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        className="pr-10"
                        disabled={isDisabled}
                        autoComplete="current-password"
                        onPaste={(e) => e.preventDefault()}
                        onCopy={(e) => e.preventDefault()}
                        onCut={(e) => e.preventDefault()}
                        onContextMenu={(e) => e.preventDefault()}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                        tabIndex={-1}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  )}
                </FormField>
              </motion.div>

              {/* CAPTCHA Field */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.18 }}
                className="space-y-2"
              >
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-12 bg-white dark:bg-gray-800 rounded-md border flex items-center justify-center relative overflow-hidden">
                    {/* Noise/Pattern Background - Removed for visibility stability
                    <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                    */}

                    {captchaLoading ? (
                      <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                    ) : (
                      <span className="font-mono text-xl font-bold text-gray-900 dark:text-gray-100 tracking-[0.5em] select-none relative z-10">
                        {captchaCode || '.....'}
                      </span>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={fetchCaptcha}
                    disabled={captchaLoading || isDisabled}
                    className="h-12 w-12"
                    title="Refresh CAPTCHA"
                  >
                    <RefreshCw className={`h-4 w-4 ${captchaLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>

                <FormField
                  control={methods.control}
                  name="captcha_input"
                  label="Enter CAPTCHA"
                  placeholder="Type the characters above"
                  type="text"
                  required
                  disabled={isDisabled}
                />
              </motion.div>

              {/* Remember Me & Forgot Password */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="flex items-center justify-between"
              >
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    {...methods.register('rememberMe')}
                    disabled={isDisabled}
                    className="h-4 w-4 rounded border-input text-primary focus:ring-primary transition-colors cursor-pointer disabled:cursor-not-allowed"
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

              {/* Submit Button */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <Button
                  type="submit"
                  disabled={isDisabled}
                  className="w-full h-11 bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity"
                >
                  {lockoutTime > 0 ? (
                    `Retry in ${lockoutTime}s`
                  ) : isLoggingIn ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    'Sign in'
                  )}
                </Button>
              </motion.div>

              {/* Social Login */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <SocialLogin isLoading={isDisabled} />
              </motion.div>

              {/* Sign Up Link */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
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
    </>
  );
}

function FormKeyboardListener({ reset }: { reset: (values?: any) => void }) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
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

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}

