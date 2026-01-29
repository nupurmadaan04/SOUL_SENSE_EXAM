import { z } from 'zod';

// Utility to get validation errors in a flat structure
export const getValidationErrors = (error: z.ZodError) => {
  return error.errors.reduce(
    (acc, err) => {
      const path = err.path.join('.');
      acc[path] = err.message;
      return acc;
    },
    {} as Record<string, string>
  );
};

// Utility to validate a single field
export const validateField = <T>(
  schema: z.ZodSchema<T>,
  value: unknown
): { success: true; data: T } | { success: false; error: string } => {
  const result = schema.safeParse(value);
  if (result.success) {
    return { success: true, data: result.data };
  } else {
    return { success: false, error: result.error.errors[0]?.message || 'Validation failed' };
  }
};

// Debounce utility for async validation
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Utility to format validation messages
export const formatValidationMessage = (message: string, fieldName?: string): string => {
  if (fieldName) {
    return `${fieldName}: ${message}`;
  }
  return message;
};

// Utility to check if a schema has async refinements
export const hasAsyncRefinements = (schema: z.ZodSchema): boolean => {
  // This is a simplified check - in practice, you might need to traverse the schema
  return schema instanceof z.ZodEffects;
};

// Utility for password strength calculation
export const calculatePasswordStrength = (
  password: string
): {
  score: number;
  feedback: string[];
} => {
  const feedback: string[] = [];
  let score = 0;

  if (password.length >= 8) score++;
  else feedback.push('Use at least 8 characters');

  if (/[A-Z]/.test(password)) score++;
  else feedback.push('Add uppercase letters');

  if (/[a-z]/.test(password)) score++;
  else feedback.push('Add lowercase letters');

  if (/[0-9]/.test(password)) score++;
  else feedback.push('Add numbers');

  if (/[^A-Za-z0-9]/.test(password)) score++;
  else feedback.push('Add special characters');

  return { score, feedback };
};
