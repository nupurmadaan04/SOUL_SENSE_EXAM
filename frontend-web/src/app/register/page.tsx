'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { AuthLayout, SocialLogin, PasswordStrengthIndicator } from '@/components/auth';
import { registrationSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';
import { useDebounce } from '@/hooks/useDebounce';
import { useEffect, useState, useMemo } from 'react';
import { cn } from '@/lib/utils';

type RegisterFormData = z.infer<typeof registrationSchema>;

interface RegisterFormContentProps {
  methods: UseFormReturn<RegisterFormData>;
  isLoading: boolean;
  setShowPassword: (show: boolean) => void;
  showPassword: boolean;
}

function RegisterFormContent({
  methods,
  isLoading,
  setShowPassword,
  showPassword,
}: RegisterFormContentProps) {
  const [availabilityStatus, setAvailabilityStatus] = useState<
    'idle' | 'loading' | 'available' | 'taken' | 'invalid'
  >('idle');

  // Local cache to prevent redundant API calls
  const availabilityCache = useMemo(
    () => new Map<string, { available: boolean; message: string }>(),
    []
  );

  const usernameValue = methods.watch('username');
  const debouncedUsername = useDebounce(usernameValue, 500);

  useEffect(() => {
    if (!debouncedUsername || debouncedUsername.length < 3) {
      setAvailabilityStatus('idle');
      return;
    }

    // Client-side reserved words check
    const reserved = ['admin', 'root', 'support', 'soulsense', 'system', 'official'];
    if (reserved.includes(debouncedUsername.toLowerCase())) {
      setAvailabilityStatus('taken');
      return;
    }

    if (availabilityCache.has(debouncedUsername)) {
      setAvailabilityStatus(
        availabilityCache.get(debouncedUsername)!.available ? 'available' : 'taken'
      );
      return;
    }

    const checkAvailability = async () => {
      setAvailabilityStatus('loading');
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/auth/check-username?username=${debouncedUsername}`
        );
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        availabilityCache.set(debouncedUsername, data);
        setAvailabilityStatus(data.available ? 'available' : 'taken');
      } catch (error) {
        console.error('Error checking username availability:', error);
        setAvailabilityStatus('idle');
      }
    };

    checkAvailability();
  }, [debouncedUsername, availabilityCache]);

  return (
    <>
      {methods.formState.errors.root && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs p-3 rounded-md flex items-center mb-4">
          <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
          {methods.formState.errors.root.message}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <FormField
            control={methods.control}
            name="firstName"
            label="First name"
            placeholder="John"
            required
            disabled={isLoading}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
        >
          <FormField
            control={methods.control}
            name="lastName"
            label="Last name"
            placeholder="Doe"
            disabled={isLoading}
          />
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        <FormField
          control={methods.control}
          name="username"
          label="Username"
          placeholder="johndoe"
          required
          disabled={isLoading}
        >
          {(fieldProps) => (
            <div className="relative">
              <Input
                {...fieldProps}
                className={cn(
                  fieldProps.className,
                  availabilityStatus === 'available' &&
                    'border-green-500 focus-visible:ring-green-500',
                  availabilityStatus === 'taken' && 'border-red-500 focus-visible:ring-red-500'
                )}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                {availabilityStatus === 'loading' && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {availabilityStatus === 'available' && (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                )}
                {availabilityStatus === 'taken' && <XCircle className="h-4 w-4 text-red-500" />}
              </div>
              {availabilityStatus === 'taken' && (
                <p className="text-[10px] text-red-500 mt-1 absolute -bottom-4 left-0">
                  Username taken
                </p>
              )}
              {availabilityStatus === 'available' && (
                <p className="text-[10px] text-green-500 mt-1 absolute -bottom-4 left-0">
                  Available
                </p>
              )}
            </div>
          )}
        </FormField>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.25 }}
      >
        <FormField
          control={methods.control}
          name="email"
          label="Email"
          placeholder="you@example.com"
          type="email"
          required
          disabled={isLoading}
        />
      </motion.div>

      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <FormField
            control={methods.control}
            name="age"
            label="Age"
            placeholder="25"
            type="number"
            required
            disabled={isLoading}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.35 }}
        >
          <FormField control={methods.control} name="gender" label="Gender" required>
            {(fieldProps) => (
              <select
                {...fieldProps}
                disabled={isLoading}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
                <option value="Prefer not to say">Prefer not to say</option>
              </select>
            )}
          </FormField>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.4 }}
      >
        <FormField control={methods.control} name="password" label="Password" required>
          {(fieldProps) => (
            <div className="relative space-y-2">
              <Input
                {...fieldProps}
                type={showPassword ? 'text' : 'password'}
                disabled={isLoading}
                autoComplete="new-password"
              />
              <PasswordStrengthIndicator password={fieldProps.value || ''} />
            </div>
          )}
        </FormField>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.45 }}
      >
        <FormField
          control={methods.control}
          name="confirmPassword"
          label="Confirm Password"
          required
        >
          {(fieldProps) => (
            <div className="relative">
              <Input
                {...fieldProps}
                type={showPassword ? 'text' : 'password'}
                disabled={isLoading}
                autoComplete="new-password"
              />
            </div>
          )}
        </FormField>
      </motion.div>

      <div className="flex items-center space-x-2 mb-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setShowPassword(!showPassword)}
          disabled={isLoading}
          className="text-xs h-8"
        >
          {showPassword ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
          {showPassword ? 'Hide' : 'Show'} password
        </Button>
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5 }}
      >
        <FormField control={methods.control} name="acceptTerms">
          {(fieldProps) => (
            <div className="flex items-start space-x-3 mb-4">
              <input
                type="checkbox"
                id="acceptTerms"
                checked={fieldProps.value || false}
                onChange={(e) => fieldProps.onChange(e.target.checked)}
                disabled={isLoading}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
              />
              <label
                htmlFor="acceptTerms"
                className="text-xs text-muted-foreground cursor-pointer leading-tight"
              >
                I agree to the{' '}
                <Link
                  href="/terms"
                  className="text-primary hover:text-primary/80 underline"
                  target="_blank"
                >
                  Terms & Conditions
                </Link>
              </label>
            </div>
          )}
        </FormField>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.55 }}
      >
        <Button
          type="submit"
          className="w-full"
          disabled={isLoading || availabilityStatus === 'loading' || availabilityStatus === 'taken'}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Registering...
            </>
          ) : (
            'Register'
          )}
        </Button>
      </motion.div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
        <SocialLogin isLoading={isLoading} />
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.65 }}
        className="text-center text-sm text-muted-foreground mt-4"
      >
        Already have an account?{' '}
        <Link
          href="/login"
          className="text-primary hover:text-primary/80 font-medium transition-colors"
        >
          Sign in
        </Link>
      </motion.p>
    </>
  );
}

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (data: RegisterFormData, methods: UseFormReturn<RegisterFormData>) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: data.username,
          password: data.password,
          email: data.email,
          first_name: data.firstName,
          last_name: data.lastName,
          age: data.age,
          gender: data.gender,
        }),
      });

      if (response.ok) {
        router.push('/login?registered=true');
      } else {
        const errorData = await response.json();
        const code = errorData.detail?.code;

        if (code === 'REG001') {
          methods.setError('username', { message: 'Username already taken' });
        } else if (code === 'REG002') {
          methods.setError('email', { message: 'Email already registered' });
        } else if (code === 'REG006') {
          methods.setError('password', { message: 'This password is too common. Please choose a stronger password.' });
        } else {
          methods.setError('root', { message: errorData.detail?.message || 'Registration failed' });
        }
      }
    } catch (error) {
      methods.setError('root', {
        message: 'Network error. Please check your connection and try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start your emotional intelligence journey today"
    >
      <Form
        schema={registrationSchema}
        onSubmit={handleSubmit}
        className={`space-y-4 transition-opacity duration-200 ${isLoading ? 'opacity-60 pointer-events-none' : ''}`}
      >
        {(methods) => (
          <RegisterFormContent
            methods={methods}
            isLoading={isLoading}
            setShowPassword={setShowPassword}
            showPassword={showPassword}
          />
        )}
      </Form>
    </AuthLayout>
  );
}
