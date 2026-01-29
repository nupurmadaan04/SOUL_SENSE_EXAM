import { z } from 'zod';
import {
  loginSchema,
  registrationSchema,
  profileUpdateSchema,
  passwordChangeSchema,
  registrationSchemaWithAsync,
} from './schemas';

// Inferred types from schemas
export type LoginFormData = z.infer<typeof loginSchema>;
export type RegistrationFormData = z.infer<typeof registrationSchema>;
export type ProfileUpdateFormData = z.infer<typeof profileUpdateSchema>;
export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;
export type RegistrationFormDataWithAsync = z.infer<typeof registrationSchemaWithAsync>;

// Generic form field props
export interface FormFieldProps {
  name: string;
  label?: string;
  placeholder?: string;
  type?: string;
  required?: boolean;
  disabled?: boolean;
}

// Form state types
export interface FormState<T> {
  data: T;
  errors: Record<string, string>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Validation result type
export type ValidationResult<T> =
  | { success: true; data: T }
  | { success: false; errors: Record<string, string> };

// Async validation function type
export type AsyncValidator<T> = (value: T) => Promise<boolean>;

// Error message type for localization
export interface ValidationErrorMessage {
  key: string;
  defaultMessage: string;
  params?: Record<string, any>;
}
