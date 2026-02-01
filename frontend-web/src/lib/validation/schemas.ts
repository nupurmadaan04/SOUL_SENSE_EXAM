import { z } from 'zod';

// Base schemas
// Enhanced email validation with stricter pattern requiring valid domain and TLD
export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .regex(
    /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    'Please enter a valid email address (e.g., name@example.com)'
  );

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character');

export const usernameSchema = z
  .string()
  .min(3, 'Username must be at least 3 characters')
  .max(20, 'Username must be at most 20 characters')
  .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores');

export const nameSchema = z
  .string()
  .min(1, 'Name is required')
  .max(50, 'Name must be at most 50 characters');

// Login schema
export const loginSchema = z.object({
  identifier: z.string().min(1, 'Email or Username is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

// Forgot password schema
export const forgotPasswordSchema = z.object({
  email: emailSchema,
});

// Registration schema
export const registrationSchema = z
  .object({
    username: usernameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string(),
    firstName: nameSchema,
    lastName: nameSchema.optional(),
    age: z.coerce.number().min(13, 'You must be at least 13 years old').max(120, 'Invalid age'),
    gender: z.enum(['Male', 'Female', 'Other', 'Prefer not to say']),
    acceptTerms: z.boolean().refine((val) => val === true, {
      message: 'You must accept the terms and conditions',
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

// Profile update schema
export const profileUpdateSchema = z.object({
  firstName: nameSchema,
  lastName: nameSchema.optional(),
  email: emailSchema,
  username: usernameSchema,
});

// Password change schema
export const passwordChangeSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: passwordSchema,
    confirmNewPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmNewPassword, {
    message: "New passwords don't match",
    path: ['confirmNewPassword'],
  });

// Async validation for uniqueness (placeholder - implement with API calls)
export const asyncEmailUnique = async (email: string): Promise<boolean> => {
  // Simulate API call
  return new Promise((resolve) => {
    setTimeout(() => {
      // In real implementation, check against API
      resolve(email !== 'taken@example.com');
    }, 500);
  });
};

export const asyncUsernameUnique = async (username: string): Promise<boolean> => {
  // Simulate API call
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(username !== 'takenuser');
    }, 500);
  });
};

// Enhanced schemas with async validation
export const registrationSchemaWithAsync = registrationSchema
  .refine(async (data) => await asyncEmailUnique(data.email), {
    message: 'Email is already taken',
    path: ['email'],
  })
  .refine(async (data) => await asyncUsernameUnique(data.username), {
    message: 'Username is already taken',
    path: ['username'],
  });
