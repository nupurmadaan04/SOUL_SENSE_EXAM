'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { AuthLayout, SocialLogin, PasswordStrengthIndicator } from '@/components/auth';
import { registrationSchema } from '@/lib/validation';
import { z } from 'zod';
import { UseFormReturn } from 'react-hook-form';

type RegisterFormData = z.infer<typeof registrationSchema>;

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (data: RegisterFormData, methods: UseFormReturn<RegisterFormData>) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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

      if (!response.ok) {
        const errorData = await response.json();
        const code = errorData.detail?.code;

        // Map backend ErrorCodes to specific form fields
        if (code === 'REG001') {
          methods.setError('username', { message: 'Username already taken' });
          return;
        }
        if (code === 'REG002') {
          methods.setError('email', { message: 'Email already registered' });
          return;
        }

        const errorMessage = errorData.detail?.message || errorData.detail || 'Registration failed';
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log('Registration successful:', result);
      window.location.href = '/login?registered=true';
    } catch (error) {
      console.error('Registration error:', error);
      // Fallback to alert for global or unexpected errors
      alert(error instanceof Error ? error.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start your emotional intelligence journey today"
    >
      <Form schema={registrationSchema} onSubmit={handleSubmit} className="space-y-4">
        {(methods) => (
          <>
            <div className="grid grid-cols-2 gap-4">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <FormField
                  control={methods.control}
                  name="firstName"
                  label="First name"
                  placeholder="John"
                  required
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <FormField
                  control={methods.control}
                  name="lastName"
                  label="Last name"
                  placeholder="Doe"
                />
              </motion.div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 }}
              >
                <FormField
                  control={methods.control}
                  name="username"
                  label="Username"
                  placeholder="johndoe"
                  required
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
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
                />
              </motion.div>
            </div>

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
                />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <FormField control={methods.control} name="gender" label="Gender" required>
                  {(fieldProps) => (
                    <select
                      {...fieldProps}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
              transition={{ delay: 0.35 }}
            >
              <FormField control={methods.control} name="password" label="Password" required>
                {(fieldProps) => (
                  <input
                    {...fieldProps}
                    type={showPassword ? 'text' : 'password'}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                )}
              </FormField>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <FormField
                control={methods.control}
                name="confirmPassword"
                label="Confirm password"
                required
              >
                {(fieldProps) => (
                  <input
                    {...fieldProps}
                    type={showPassword ? 'text' : 'password'}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                )}
              </FormField>
            </motion.div>
            <div className="flex items-center space-x-2 mb-4">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowPassword(!showPassword)}
                className="text-sm"
              >
                {showPassword ? 'Hide Password' : 'Show Password'}
              </Button>
            </div>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.45 }}
            >
              <FormField control={methods.control} name="acceptTerms">
                {(fieldProps) => (
                  <div className="flex items-start space-x-3 mb-4">
                    <input
                      type="checkbox"
                      id="acceptTerms"
                      checked={fieldProps.value || false}
                      onChange={(e) => fieldProps.onChange(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer"
                    />
                    <label
                      htmlFor="acceptTerms"
                      className="text-sm text-muted-foreground cursor-pointer"
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
              transition={{ delay: 0.5 }}
            >
              <Button type="submit" className="w-full" disabled={isLoading}>
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

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.55 }}
            >
              <SocialLogin isLoading={isLoading} />
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="text-center text-sm text-muted-foreground"
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
    </AuthLayout>
  );
}
