'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  User,
  Mail,
  Shield,
} from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import {
  AuthLayout,
  SocialLogin,
  PasswordStrengthIndicator,
  StepIndicator,
} from '@/components/auth';
import { registrationSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn, useController } from 'react-hook-form';
import { useDebounce } from '@/hooks/useDebounce';
import { useEffect, useState, useMemo, useRef, useCallback, Suspense } from 'react';
import { cn } from '@/lib/utils';
import { authApi } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/errors';
import { useRateLimiter } from '@/hooks/useRateLimiter';
import { analyticsApi } from '@/lib/api/analytics';
import { useAuth } from '@/hooks/useAuth';
import { isValidCallbackUrl } from '@/lib/utils/url';
import { toast } from 'sonner';

type RegisterFormData = z.infer<typeof registrationSchema>;

const steps = [
  { id: 'personal', label: 'Personal', description: 'Your info' },
  { id: 'account', label: 'Account', description: 'Credentials' },
  { id: 'terms', label: 'Complete', description: 'Review & submit' },
];

interface StepContentProps {
  methods: UseFormReturn<RegisterFormData>;
  isLoading: boolean;
  onNext?: () => void;
  onBack?: () => void;
  canProceed: boolean;
  handleFocus: (fieldName: string) => void;
}

interface StepProps extends StepContentProps {
  showPassword?: boolean;
  setShowPassword?: (show: boolean) => void;
  availabilityCache?: Map<string, { available: boolean; message: string }>;
}

function PersonalStep({ methods, isLoading, onNext, handleFocus }: StepProps) {
  const handleContinue = async () => {
    const isValid = await methods.trigger(['firstName', 'age', 'gender']);
    if (isValid) {
      onNext?.();
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4 text-primary">
        <User className="w-5 h-5" />
        <h3 className="font-semibold">Personal Information</h3>
      </div>

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
            onFocus={() => handleFocus('firstName')}
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
            onFocus={() => handleFocus('lastName')}
          />
        </motion.div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <FormField
            control={methods.control}
            name="age"
            label="Age"
            placeholder="25"
            type="number"
            required
            disabled={isLoading}
            onFocus={() => handleFocus('age')}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
        >
          <FormField
            control={methods.control}
            name="gender"
            label="Gender"
            required
            onFocus={() => handleFocus('gender')}
          >
            {(fieldProps) => (
              <select
                {...fieldProps}
                disabled={isLoading}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                onChange={(e) => {
                  fieldProps.onChange(e);
                  handleFocus('gender');
                }}
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
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="pt-4"
      >
        <Button type="button" onClick={handleContinue} disabled={isLoading} className="w-full">
          Continue
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </motion.div>
    </div>
  );
}

function AccountStep({
  methods,
  isLoading,
  showPassword,
  setShowPassword,
  availabilityCache,
  onNext,
  onBack,
  handleFocus,
}: StepProps) {
  const [localStatus, setLocalStatus] = useState<
    'idle' | 'loading' | 'available' | 'taken' | 'invalid'
  >('idle');

  const handleContinue = async () => {
    const isValid = await methods.trigger(['username', 'email', 'password', 'confirmPassword']);
    if (isValid && localStatus !== 'taken' && localStatus !== 'loading') {
      onNext?.();
    }
  };

  const usernameValue = methods.watch('username');
  const debouncedUsername = useDebounce(usernameValue, 500);

  useEffect(() => {
    if (!debouncedUsername || debouncedUsername.length < 3) {
      setLocalStatus('idle');
      return;
    }

    const reserved = ['admin', 'root', 'support', 'soulsense', 'system', 'official'];
    if (reserved.includes(debouncedUsername.toLowerCase())) {
      setLocalStatus('taken');
      return;
    }

    if (availabilityCache?.has(debouncedUsername)) {
      setLocalStatus(availabilityCache.get(debouncedUsername)!.available ? 'available' : 'taken');
      return;
    }

    const checkAvailability = async () => {
      setLocalStatus('loading');
      try {
        const data = await authApi.checkUsernameAvailability(debouncedUsername);
        availabilityCache?.set(debouncedUsername, data);
        setLocalStatus(data.available ? 'available' : 'taken');
      } catch (error) {
        console.error('Error checking username availability:', error);
        setLocalStatus('idle');
      }
    };

    checkAvailability();
  }, [debouncedUsername, availabilityCache]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4 text-primary">
        <Mail className="w-5 h-5" />
        <h3 className="font-semibold">Account Details</h3>
      </div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
      >
        <FormField
          control={methods.control}
          name="username"
          label="Username"
          placeholder="johndoe"
          required
          disabled={isLoading}
          onFocus={() => handleFocus('username')}
        >
          {(fieldProps) => (
            <div className="relative">
              <Input
                {...fieldProps}
                className={cn(
                  fieldProps.className,
                  localStatus === 'available' && 'border-green-500 focus-visible:ring-green-500',
                  localStatus === 'taken' && 'border-red-500 focus-visible:ring-red-500'
                )}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                {localStatus === 'loading' && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {localStatus === 'available' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                {localStatus === 'taken' && <XCircle className="h-4 w-4 text-red-500" />}
              </div>
              {localStatus === 'taken' && (
                <p className="text-[10px] text-red-500 mt-1 absolute -bottom-4 left-0">
                  Username taken
                </p>
              )}
              {localStatus === 'available' && (
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
        transition={{ delay: 0.15 }}
      >
        <FormField
          control={methods.control}
          name="email"
          label="Email"
          placeholder="you@example.com"
          type="email"
          required
          disabled={isLoading}
          onFocus={() => handleFocus('email')}
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        <FormField
          control={methods.control}
          name="password"
          label="Password"
          required
          onFocus={() => handleFocus('password')}
        >
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
        transition={{ delay: 0.25 }}
      >
        <FormField
          control={methods.control}
          name="confirmPassword"
          label="Confirm Password"
          required
          onFocus={() => handleFocus('confirmPassword')}
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

      <div className="flex items-center space-x-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setShowPassword?.(!showPassword)}
          disabled={isLoading}
          className="text-xs h-8"
        >
          {showPassword ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
          {showPassword ? 'Hide' : 'Show'} password
        </Button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex gap-3 pt-4"
      >
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={isLoading}
          className="flex-1"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button
          type="button"
          onClick={handleContinue}
          disabled={isLoading || localStatus === 'loading' || localStatus === 'taken'}
          className="flex-1"
        >
          Continue
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </motion.div>
    </div>
  );
}

function TermsStep({
  methods,
  isLoading,
  onBack,
  lockoutTime = 0,
  handleFocus,
}: StepProps & { lockoutTime?: number }) {
  const { field } = useController({
    control: methods.control,
    name: 'acceptTerms',
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4 text-primary">
        <Shield className="w-5 h-5" />
        <h3 className="font-semibold">Review & Submit</h3>
      </div>

      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm"
      >
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-muted-foreground">Name:</span>
            <p className="font-medium">
              {methods.getValues('firstName')} {methods.getValues('lastName')}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Username:</span>
            <p className="font-medium">{methods.getValues('username')}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Email:</span>
            <p className="font-medium">{methods.getValues('email')}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Age/Gender:</span>
            <p className="font-medium">
              {methods.getValues('age')} / {methods.getValues('gender')}
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex items-start space-x-3 p-3 bg-primary/5 rounded-lg border border-primary/10">
          <input
            type="checkbox"
            id="acceptTerms"
            checked={field.value || false}
            onChange={(e) => field.onChange(e.target.checked)}
            disabled={isLoading}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
            onFocus={() => handleFocus('acceptTerms')}
          />
          <label
            htmlFor="acceptTerms"
            className="text-sm text-muted-foreground cursor-pointer leading-tight"
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
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex gap-3 pt-2"
      >
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={isLoading}
          className="flex-1"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button type="submit" disabled={isLoading || !field.value} className="flex-1">
          {isLoading && lockoutTime > 0 ? (
            `Retry in ${lockoutTime}s`
          ) : isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Account...
            </>
          ) : (
            <>
              <Shield className="mr-2 h-4 w-4" />
              Create Account
            </>
          )}
        </Button>
      </motion.div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
        <SocialLogin isLoading={isLoading} />
      </motion.div>
    </div>
  );
}

function RegisterContent() {
  const [currentStep, setCurrentStep] = useState(0);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/';
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  // Guard: Redirect if already logged in
  useEffect(() => {
    if (!authLoading && isAuthenticated && !isLoading && !isSuccess) {
      const finalRedirect = isValidCallbackUrl(callbackUrl) && callbackUrl !== '/' ? callbackUrl : '/dashboard';
      router.push(finalRedirect);
    }
  }, [isAuthenticated, authLoading, isLoading, isSuccess, router, callbackUrl]);

  const { lockoutTime, isLocked, handleRateLimitError } = useRateLimiter();

  const availabilityCache = useMemo(
    () => new Map<string, { available: boolean; message: string }>(),
    []
  );

  // Analytics: Track field interactions
  const trackedFields = useRef<Set<string>>(new Set());
  const handleFocus = useCallback((fieldName: string) => {
    if (!trackedFields.current.has(fieldName)) {
      trackedFields.current.add(fieldName);
      analyticsApi.trackEvent({
        event_type: 'signup_workflow',
        event_name: 'field_focus',
        event_data: { field: fieldName },
      });
    }
  }, []);

  // Analytics: Track page view
  useEffect(() => {
    analyticsApi.trackEvent({
      event_type: 'signup_workflow',
      event_name: 'signup_view',
    });
  }, []);

  const validateStep = useCallback(
    (step: number, methods: UseFormReturn<RegisterFormData>): boolean => {
      const values = methods.getValues();
      const errors = methods.formState.errors;

      switch (step) {
        case 0: // Personal
          return (
            !!values.firstName &&
            !!values.age &&
            !!values.gender &&
            !errors.firstName &&
            !errors.age &&
            !errors.gender
          );
        case 1: // Account
          return (
            !!values.username &&
            !!values.email &&
            !!values.password &&
            !!values.confirmPassword &&
            !errors.username &&
            !errors.email &&
            !errors.password &&
            !errors.confirmPassword
          );
        case 2: // Terms
          return !!values.acceptTerms;
        default:
          return false;
      }
    },
    []
  );

  const handleNext = useCallback((methods: UseFormReturn<RegisterFormData>) => {
    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
  }, []);

  const handleBack = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  }, []);

  const handleSubmit = async (data: RegisterFormData, methods: UseFormReturn<RegisterFormData>) => {
    if (isLocked) return;

    // Analytics: Track submit attempt
    analyticsApi.trackEvent({
      event_type: 'signup_workflow',
      event_name: 'signup_submit',
    });

    setIsLoading(true);
    try {
      const result = await authApi.register({
        username: data.username,
        password: data.password,
        email: data.email || '',
        first_name: data.firstName,
        last_name: data.lastName || '',
        age: data.age,
        gender: data.gender,
      });

      setSuccessMessage(
        result.message || 'Registration request received. Please check your email for next steps.'
      );

      // Analytics: Track success
      analyticsApi.trackEvent({
        event_type: 'signup_workflow',
        event_name: 'signup_success',
      });

      // Flag for one-time new user onboarding wizard
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('soulsense_welcome_session', 'true');
        sessionStorage.setItem('soulsense_just_signed_up', 'true');
      }

      // AUTOMATIC LOGIN DIRECTLY TO DASHBOARD
      const targetDestination = isValidCallbackUrl(callbackUrl) && callbackUrl !== '/' ? callbackUrl : '/dashboard';
      try {
        await login(
          {
            username: data.username,
            password: data.password,
          },
          true, // rememberMe
          true, // shouldRedirect
          targetDestination
        );
      } catch (loginError) {
        console.warn('Auto-login after registration failed, redirecting to dashboard:', loginError);
        router.push(targetDestination);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        const result = error.data || {};

        if (
          handleRateLimitError(result, (msg: string) => methods.setError('root', { message: msg }))
        ) {
          return;
        }

        let errorMessage = result.message;
        if (!errorMessage && result.detail) {
          if (Array.isArray(result.detail)) {
            errorMessage = result.detail[0]?.msg;
          } else if (typeof result.detail === 'string') {
            errorMessage = result.detail;
          } else if (result.detail.message) {
            errorMessage = result.detail.message;
          }
        }

        methods.setError('root', {
          message: errorMessage || 'Registration failed. Please try again or contact support.',
        });
        toast.error(errorMessage || 'Registration failed. Please try again.');

        analyticsApi.trackEvent({
          event_type: 'signup_workflow',
          event_name: 'signup_error',
          event_data: { error: errorMessage || 'Registration failed' },
        });
      } else {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('Registration non-api error:', error);
        methods.setError('root', {
          message: `Registration encountered an unexpected error: ${errorMsg}. Please try again or contact support.`,
        });
        toast.error(`Registration error: ${errorMsg}`);

        analyticsApi.trackEvent({
          event_type: 'signup_workflow',
          event_name: 'signup_network_error',
          event_data: { error: errorMsg },
        });
        setCurrentStep(2);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const effectiveLoading = isLoading || isLocked;

  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start your emotional intelligence journey today"
    >
      {isSuccess ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center space-y-4 py-8"
        >
          <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold">Verify your email</h3>
          <p className="text-muted-foreground">{successMessage}</p>
          <Button onClick={() => router.push('/login')} className="mt-4">
            Back to Login
          </Button>
        </motion.div>
      ) : (
        <Form
          schema={registrationSchema}
          onSubmit={handleSubmit}
          defaultValues={{
            firstName: '',
            lastName: '',
            age: 18,
            gender: undefined,
            username: '',
            email: '',
            password: '',
            confirmPassword: '',
            acceptTerms: false,
          }}
          className={`space-y-6 transition-opacity duration-200 ${effectiveLoading ? 'opacity-60' : ''}`}
        >
          {(methods) => (
            <>
              <StepIndicator steps={steps} currentStep={currentStep} className="mb-6" />

              {methods.formState.errors.root && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-destructive/10 border border-destructive/20 text-destructive text-xs p-3 rounded-md flex items-center"
                >
                  <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                  {methods.formState.errors.root.message}
                </motion.div>
              )}

              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  {currentStep === 0 && (
                    <PersonalStep
                      methods={methods}
                      isLoading={effectiveLoading}
                      onNext={() => handleNext(methods)}
                      handleFocus={handleFocus}
                      canProceed={validateStep(0, methods)}
                    />
                  )}
                  {currentStep === 1 && (
                    <AccountStep
                      methods={methods}
                      isLoading={effectiveLoading}
                      showPassword={showPassword}
                      setShowPassword={setShowPassword}
                      availabilityCache={availabilityCache}
                      onNext={() => handleNext(methods)}
                      onBack={handleBack}
                      handleFocus={handleFocus}
                      canProceed={validateStep(1, methods)}
                    />
                  )}
                  {currentStep === 2 && (
                    <TermsStep
                      methods={methods}
                      isLoading={effectiveLoading}
                      onBack={handleBack}
                      handleFocus={handleFocus}
                      canProceed={validateStep(2, methods)}
                      lockoutTime={lockoutTime}
                    />
                  )}
                </motion.div>
              </AnimatePresence>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="text-center text-sm text-muted-foreground pt-4"
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
          )}
        </Form>
      )}
    </AuthLayout>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
