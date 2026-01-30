'use client';

import React, { useState } from 'react';
import { Form } from '@/components/forms';
import { FormField } from '@/components/forms';
import { Button } from '@/components/ui';
import { z } from 'zod';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function Register() {
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (data: RegisterFormData) => {
    // TODO: Implement registration logic
    console.log('Register data:', data);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Register</h1>
        <Form schema={registerSchema} onSubmit={handleSubmit}>
          {(methods) => (
            <>
              <FormField
                control={methods.control}
                name="email"
                label="Email"
                placeholder="Enter your email"
                required
              />
              <FormField
                control={methods.control}
                name="password"
                label="Password"
                placeholder="Enter your password"
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
              <FormField
                control={methods.control}
                name="confirmPassword"
                label="Confirm Password"
                placeholder="Confirm your password"
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
              <div className="flex items-center space-x-2 mb-4">
                <input
                  type="checkbox"
                  id="showPassword"
                  checked={showPassword}
                  onChange={(e) => setShowPassword(e.target.checked)}
                  className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                />
                <label htmlFor="showPassword" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Show Password
                </label>
              </div>
              <Button type="submit" className="w-full">
                Register
              </Button>
            </>
          )}
        </Form>
      </div>
    </div>
  );
}
