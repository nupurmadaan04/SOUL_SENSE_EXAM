'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { AuthLayout, SocialLogin, ForgotPasswordModal } from '@/components/auth';
import { loginSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';

import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/lib/api/errors';

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

  // Lockout State
  const [lockoutTime, setLockoutTime] = useState<number>(0);

  // CAPTCHA State (from main)
  const [captchaCode, setCaptchaCode] = useState('');
  const [userCaptchaInput, setUserCaptchaInput] = useState('');
  const [captchaError, setCaptchaError] = useState('');
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [captchaAttempts, setCaptchaAttempts] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Forgot Password Modal State (from main)
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  // CAPTCHA State
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [captchaCode, setCaptchaCode] = useState('');
  const [userCaptchaInput, setUserCaptchaInput] = useState('');
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [captchaError, setCaptchaError] = useState('');
  const [captchaAttempts, setCaptchaAttempts] = useState(0);

  const generateCaptcha = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
    let code = '';
    for (let i = 0; i < 5; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaCode(code);
    setUserCaptchaInput('');
    setCaptchaVerified(false);
    setCaptchaError('');
    setCaptchaAttempts(0);
    drawCaptcha(code);
  };

  useEffect(() => {
    generateCaptcha();
  }, []);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (lockoutTime > 0) {
      timer = setInterval(() => {
        setLockoutTime((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [lockoutTime]);

  const generateCaptcha = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let result = '';
    for (let i = 0; i < 5; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaCode(result);
    // Draw captcha after state update
    setTimeout(() => drawCaptcha(result), 0);
  };

  const drawCaptcha = (text: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Add noise dots
    for (let i = 0; i < 50; i++) {
      ctx.fillStyle = `rgba(${Math.random() * 100 + 155}, ${Math.random() * 100 + 155}, ${Math.random() * 100 + 155}, 0.3)`;
      ctx.beginPath();
      ctx.arc(
        Math.random() * canvas.width,
        Math.random() * canvas.height,
        Math.random() * 2,
        0,
        Math.PI * 2
      );
      ctx.fill();
    }

    // Add noise lines
    for (let i = 0; i < 3; i++) {
      ctx.strokeStyle = `rgba(${Math.random() * 100 + 155}, ${Math.random() * 100 + 155}, ${Math.random() * 100 + 155}, 0.2)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
      ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
      ctx.stroke();
    }

    // Draw text
    const fontSizes = [24, 26, 28, 30];
    const fonts = ['Arial', 'Verdana', 'Georgia', 'Times New Roman'];

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      const x = 20 + i * 25 + Math.random() * 10 - 5;
      const y = 35 + Math.random() * 10 - 5;

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate((Math.random() - 0.5) * 0.3); // Slight rotation

      ctx.font = `${fontSizes[Math.floor(Math.random() * fontSizes.length)]}px ${fonts[Math.floor(Math.random() * fonts.length)]}`;
      ctx.fillStyle = `hsl(${Math.random() * 360}, 70%, 40%)`;
      ctx.fillText(char, 0, 0);

      ctx.restore();
    }
  };

  const validateCaptcha = () => {
    if (captchaAttempts >= 3) {
      setCaptchaError('Too many failed attempts. CAPTCHA regenerated.');
      generateCaptcha();
      setCaptchaAttempts(0);
      return false;
    }

    if (userCaptchaInput.toLowerCase() === captchaCode.toLowerCase()) {
      setCaptchaVerified(true);
      setCaptchaError('');
      return true;
    } else {
      setCaptchaAttempts((prev) => prev + 1);
      setCaptchaError('Invalid CAPTCHA. Please try again.');
      setCaptchaVerified(false);
      return false;
    }
  };

  const handleCaptchaInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUserCaptchaInput(e.target.value);
    setCaptchaError('');
  };

  const handleCaptchaSubmit = () => {
    validateCaptcha();
  };

  const { login, login2FA } = useAuth();

  const handleLoginSubmit = async (data: LoginFormData, methods: UseFormReturn<LoginFormData>) => {
    // Preserve local storage pattern from main
    localStorage.setItem('last_used_identifier', data.identifier);

    if (lockoutTime > 0) return;
    if (!navigator.onLine) {
      methods.setError('root', {
        message: 'You are currently offline. Please check your internet connection.',
      });
      return;
    }

    // Validate CAPTCHA first (from main)
    if (!captchaVerified) {
      setCaptchaError('Please verify the CAPTCHA first.');
      return;
    }

    setIsLoggingIn(true);
    try {
      // Use updated hook with JSON-compatible parameters
      const result = await login(
        {
          username: data.identifier,
          password: data.password,
          captcha_input: userCaptchaInput,
          session_id: 'browser-session', // Optional, can be refined
        },
        !!data.rememberMe
      );

      if (result?.pre_auth_token) {
        setPreAuthToken(result.pre_auth_token);
        setShow2FA(true);
      }
    } catch (error: any) {
      console.error('Login error:', error);

      let errorMessage = 'Login failed. Please try again.';

      if (error instanceof ApiError) {
        if (error.isNetworkError) {
          errorMessage =
            'Connection failed. Please check if your server is running and you have internet access.';
        } else if (error.status === 401) {
          const detail = error.detail;
          if (detail?.code === 'AUTH001') {
            methods.setError('identifier', { message: 'Invalid username/email or password' });
            return;
          }
          errorMessage = detail?.message || 'Invalid credentials';
        } else if (error.status === 429) {
          const waitSeconds = error.detail?.details?.wait_seconds || 60;
          setLockoutTime(waitSeconds);
          errorMessage = `Too many attempts. Account locked for ${waitSeconds} seconds.`;
        } else {
          errorMessage = error.message;
        }
      }

      methods.setError('root', { message: errorMessage });
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (!navigator.onLine) {
      setTwoFaError('You are currently offline.');
      return;
    }

    setIsLoggingIn(true);
    setTwoFaError('');
    try {
      await login2FA(
        {
          pre_auth_token: preAuthToken,
          code: otpCode,
        },
        true
      );
    } catch (error: any) {
      let errorMessage = 'Verification failed. Please try again.';
      if (error instanceof ApiError) {
        if (error.isNetworkError) {
          errorMessage = 'Connection lost. Please check your internet.';
        } else {
          errorMessage = error.message;
        }
      }
      setTwoFaError(errorMessage);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const isLoading = isLoggingIn || lockoutTime > 0; // Alias for the UI

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
    <>
      <AuthLayout title="Welcome back" subtitle="Enter your credentials to access your account">
        <Form
          schema={loginSchema}
          onSubmit={handleLoginSubmit}
          className={`space-y-5 transition-opacity duration-200 ${isLoading ? 'opacity-60 pointer-events-none' : ''}`}
        >
          {(methods) => (
            <>
              {methods.formState.errors.root && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs p-3 rounded-md flex items-center mb-5 text-red-600 bg-red-50">
                  <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                  {lockoutTime > 0
                    ? `Too many failed attempts. Please try again in ${lockoutTime}s`
                    : methods.formState.errors.root.message}
                </div>
              )}
              <FormKeyboardListener reset={methods.reset} />
              <RestoreSavedIdentifier setValue={methods.setValue} />

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

              {/* CAPTCHA Section (from main) */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.275 }}
                className="space-y-3"
              >
                <label className="text-sm font-medium leading-none">CAPTCHA Verification</label>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <canvas
                      ref={canvasRef}
                      width={150}
                      height={50}
                      className="border border-input rounded-md bg-muted"
                      style={{ imageRendering: 'pixelated' }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={generateCaptcha}
                      className="px-3"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="flex gap-2">
                    <Input
                      value={userCaptchaInput}
                      onChange={handleCaptchaInputChange}
                      placeholder="Enter CAPTCHA"
                      className="flex-1"
                      maxLength={5}
                    />
                    <Button
                      type="button"
                      onClick={handleCaptchaSubmit}
                      disabled={!userCaptchaInput || captchaVerified}
                      variant={captchaVerified ? 'default' : 'outline'}
                      size="sm"
                    >
                      {captchaVerified ? '✓' : 'Verify'}
                    </Button>
                  </div>

                  {captchaError && <p className="text-sm text-destructive">{captchaError}</p>}
                  {captchaVerified && (
                    <p className="text-sm text-green-600 flex items-center gap-1">
                      ✓ CAPTCHA verified successfully
                    </p>
                  )}
                </div>
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
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="text-sm text-primary hover:text-primary/80 transition-colors"
                >
                  Forgot password?
                </button>
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
                      {lockoutTime > 0 ? (
                        `Retry in ${lockoutTime}s`
                      ) : (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Signing in...
                        </>
                      )}
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

      {/* Forgot Password Modal (from main) */}
      <ForgotPasswordModal
        isOpen={showForgotPassword}
        onClose={() => setShowForgotPassword(false)}
      />
    </>
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
          captchaInput: '',
          rememberMe: false,
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [reset]);

  return null;
}

function RestoreSavedIdentifier({ setValue }: { setValue: any }) {
  useEffect(() => {
    const saved = localStorage.getItem('last_used_identifier');
    if (saved) {
      setValue('identifier', saved);
    }
  }, [setValue]);
  return null;
}
