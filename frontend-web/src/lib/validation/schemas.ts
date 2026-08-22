import { z } from 'zod';
import { isWeakPassword } from './weak-passwords';

// Base schemas
// Enhanced email validation with stricter pattern requiring valid domain and TLD
export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .trim()
  .toLowerCase()
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
  .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character')
  .refine((val) => !isWeakPassword(val), {
    message: 'This password is too common. Please choose a stronger password.',
  });

const reservedUsernames = ['admin', 'root', 'support', 'soulsense', 'system', 'official'];

export const usernameSchema = z
  .string()
  .min(3, 'Username must be at least 3 characters')
  .max(20, 'Username must be at most 20 characters')
  .trim()
  .toLowerCase()
  .regex(
    /^[a-zA-Z][a-zA-Z0-9_]*$/,
    'Username must start with a letter and contain only letters, numbers, and underscores'
  )
  .refine((val) => !reservedUsernames.includes(val), {
    message: 'This username is reserved',
  });

export const nameSchema = z
  .string()
  .trim()
  .min(1, 'Name is required')
  .max(50, 'Name must be at most 50 characters');

export const optionalNameSchema = z
  .string()
  .trim()
  .max(50, 'Name must be at most 50 characters')
  .optional()
  .or(z.literal(''));

// Login schema
export const loginSchema = z.object({
  identifier: z.string().trim().toLowerCase().min(1, 'Email or Username is required'),
  password: z.string().min(1, 'Password is required'),
  captcha_input: z.string().min(1, 'CAPTCHA is required'),
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
    lastName: optionalNameSchema,
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
  lastName: optionalNameSchema,
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

// Password reset verify schema
export const resetPasswordSchema = z
  .object({
    email: emailSchema,
    otp: z.string().length(6, 'Code must be exactly 6 digits'),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

export type PasswordResetComplete = z.infer<typeof resetPasswordSchema>;

// Contact Us schema
export const contactSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(100, 'Name must be at most 100 characters'),
  email: emailSchema,
  subject: z
    .string()
    .min(5, 'Subject must be at least 5 characters')
    .max(200, 'Subject must be at most 200 characters'),
  message: z
    .string()
    .min(10, 'Message must be at least 10 characters')
    .max(2000, 'Message must be at most 2000 characters'),
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

// AI Boundaries schema
export const aiBoundariesSchema = z.object({
  off_limit_topics: z
    .array(z.string()
      .min(1)
      .regex(/^[^<>/]*$/, 'Topic cannot contain systemic symbols (<, >, /)'))
    .max(20, 'Maximum of 20 off-limit topics allowed'),
  ai_tone_preference: z.enum(['Clinical', 'Warm', 'Direct', 'Philosophical']),
  storage_retention_days: z.number().min(1).max(3650),
});

export const userSettingsSchema = z.object({
  theme: z.enum(['light', 'dark', 'system']),
  notifications: z.object({
    email: z.boolean(),
    push: z.boolean(),
    frequency: z.enum(['immediate', 'daily', 'weekly']),
    types: z.object({
      exam_reminders: z.boolean(),
      journal_prompts: z.boolean(),
      progress_updates: z.boolean(),
      system_updates: z.boolean(),
    }),
  }),
  privacy: z.object({
    data_collection: z.boolean(),
    analytics: z.boolean(),
    data_retention_days: z.number(),
    profile_visibility: z.enum(['public', 'private', 'friends']),
  }),
  ai_boundaries: aiBoundariesSchema,
});

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


