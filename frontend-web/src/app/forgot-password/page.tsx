'use client';

import React, { useState } from 'react';
import { Form } from '@/components/forms';
import { FormField } from '@/components/forms';
import { Button } from '@/components/ui';
import { z } from 'zod';

const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPassword() {
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (data: ForgotPasswordFormData) => {
    try {
      // TODO: Implement API call to reset password
      console.log('Reset password for:', data.email);

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Simulate success
      setIsSuccess(true);
      setMessage('Password reset successfully! You can now login with your new password.');
    } catch (error) {
      setIsSuccess(false);
      setMessage('Failed to reset password. Please try again.');
    }
  };

  if (isSuccess) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-center mb-6">Password Reset Successful</h1>
          <div className="text-center">
            <div className="text-green-600 mb-4">{message}</div>
            <Button
              onClick={() => window.location.href = '/login'}
              className="w-full"
            >
              Back to Login
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Reset Password</h1>
        <Form schema={forgotPasswordSchema} onSubmit={handleSubmit}>
          {(methods) => (
            <>
              <FormField
                control={methods.control}
                name="email"
                label="Email"
                placeholder="Enter your email address"
                required
              />
              <FormField
                control={methods.control}
                name="newPassword"
                label="New Password"
                placeholder="Enter your new password"
                required
              >
                {(fieldProps) => (
                  <div className="relative">
                    <input
                      {...fieldProps}
                      type={showNewPassword ? 'text' : 'password'}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                      <input
                        type="checkbox"
                        checked={showNewPassword}
                        onChange={(e) => setShowNewPassword(e.target.checked)}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                        title="Show Password"
                      />
                    </div>
                  </div>
                )}
              </FormField>
              <FormField
                control={methods.control}
                name="confirmPassword"
                label="Confirm New Password"
                placeholder="Confirm your new password"
                required
              >
                {(fieldProps) => (
                  <input
                    {...fieldProps}
                    type={showConfirmPassword ? 'text' : 'password'}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                )}
              </FormField>
              <div className="flex items-center space-x-2 mb-4">
                <input
                  type="checkbox"
                  id="showConfirmPassword"
                  checked={showConfirmPassword}
                  onChange={(e) => setShowConfirmPassword(e.target.checked)}
                  className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                />
                <label htmlFor="showConfirmPassword" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  Show Confirm Password
                </label>
              </div>
              {message && (
                <div className={`text-sm mb-4 ${isSuccess ? 'text-green-600' : 'text-red-600'}`}>
                  {message}
                </div>
              )}
              <Button type="submit" className="w-full">
                Reset Password
              </Button>
              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={() => window.location.href = '/login'}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Back to Login
                </button>
              </div>
            </>
          )}
        </Form>
      </div>
    </div>
  );
}