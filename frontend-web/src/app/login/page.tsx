'use client';

import React, { useState } from 'react';
import { Form } from '@/components/forms';
import { FormField } from '@/components/forms';
import { Button } from '@/components/ui';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  captcha: z.string().min(1, 'Please enter the CAPTCHA code'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [captchaCode, setCaptchaCode] = useState('');
  const [captchaError, setCaptchaError] = useState('');

  // Generate random CAPTCHA code (5 characters: letters + digits)
  const generateCaptcha = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 5; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  };

  // Initialize CAPTCHA on component mount
  React.useEffect(() => {
    setCaptchaCode(generateCaptcha());
  }, []);

  const refreshCaptcha = () => {
    setCaptchaCode(generateCaptcha());
    setCaptchaError('');
  };

  const handleSubmit = async (data: LoginFormData) => {
    // Clear previous CAPTCHA error
    setCaptchaError('');

    // Validate CAPTCHA first (case-insensitive)
    if (data.captcha.toUpperCase() !== captchaCode) {
      setCaptchaError('Invalid CAPTCHA. Please try again!');
      // Clear CAPTCHA input and regenerate
      data.captcha = '';
      refreshCaptcha();
      return;
    }

    // CAPTCHA is valid, proceed with authentication
    try {
      // TODO: Implement actual login logic
      console.log('Login data:', { email: data.email, password: data.password });
      // Simulate login failure for demo
      // In real implementation, this would be an API call
      throw new Error('Invalid username or password.');
    } catch (error) {
      setCaptchaError('Invalid username or password.');
      // Regenerate CAPTCHA on login failure
      refreshCaptcha();
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Login</h1>
        <Form schema={loginSchema} onSubmit={handleSubmit}>
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
              {/* CAPTCHA Section */}
              <div className="space-y-2 mb-4">
                <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                  CAPTCHA Verification
                </label>
                <div className="flex items-center space-x-2">
                  <div className="flex-1">
                    <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-lg font-mono font-bold text-center tracking-wider bg-gray-100">
                      {captchaCode}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={refreshCaptcha}
                    className="px-3"
                  >
                    ↻
                  </Button>
                </div>
                <FormField
                  control={methods.control}
                  name="captcha"
                  label="Enter CAPTCHA"
                  placeholder="Enter the code above"
                  required
                />
                {captchaError && (
                  <p className="text-sm text-red-600">{captchaError}</p>
                )}
              </div>
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
                Login
              </Button>
            </>
          )}
        </Form>
      </div>
    </div>
  );
}
