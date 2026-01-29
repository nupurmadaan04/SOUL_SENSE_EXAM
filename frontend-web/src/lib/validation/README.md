# Form Validation System with Zod

This directory contains a comprehensive form validation system built with Zod schemas for type-safe form management in the SOUL SENSE application.

## Features

- **Zod Schemas**: Comprehensive validation schemas for user registration, login, profile updates
- **TypeScript Types**: Automatically generated types from Zod schemas
- **React Hook Form Integration**: Seamless integration with React Hook Form using @hookform/resolvers
- **Reusable Components**: Generic form wrapper, field components, error display, and validation messages
- **Custom Validations**: Password strength, email format, username rules
- **Async Validation**: Support for checking uniqueness with debounced API calls
- **Cross-field Validation**: Password confirmation, terms acceptance
- **Error Localization**: Structure for translating validation messages
- **Form State Management**: Validation status and submission handling

## Directory Structure

```
src/lib/validation/
├── schemas.ts      # Zod validation schemas
├── utils.ts        # Validation utilities and helpers
├── types.ts        # TypeScript types inferred from schemas
└── index.ts        # Barrel exports

src/components/forms/
├── Form.tsx        # Generic form wrapper component
├── FormField.tsx   # Field component with validation
├── FormError.tsx   # Error display component
├── FormLabel.tsx   # Accessible label component
├── FormMessage.tsx # Validation message display
└── index.ts        # Component exports
```

## Usage

### Basic Form Usage

```tsx
import { Form, FormField } from '@/components/forms';
import { registrationSchema, type RegistrationFormData } from '@/lib/validation';

function RegistrationForm() {
  const onSubmit = async (data: RegistrationFormData) => {
    // Handle form submission
    console.log('Form data:', data);
  };

  return (
    <Form schema={registrationSchema} onSubmit={onSubmit}>
      {(methods) => (
        <>
          <FormField control={methods.control} name="username" label="Username" required />
          <FormField control={methods.control} name="email" label="Email" type="email" required />
          <FormField
            control={methods.control}
            name="password"
            label="Password"
            type="password"
            required
          />
          <button type="submit" disabled={methods.formState.isSubmitting}>
            Register
          </button>
        </>
      )}
    </Form>
  );
}
```

### Available Schemas

- `loginSchema`: Email and password validation
- `registrationSchema`: Full registration with password confirmation
- `profileUpdateSchema`: Profile update validation
- `passwordChangeSchema`: Password change with confirmation
- `registrationSchemaWithAsync`: Registration with async uniqueness checks

### Custom Validation Rules

- **Password Strength**: Minimum 8 characters, uppercase, lowercase, number, special character
- **Email Format**: Standard email validation
- **Username**: 3-20 characters, alphanumeric + underscore
- **Name Fields**: 1-50 characters
- **Async Uniqueness**: Email and username availability checks

### Utilities

- `getValidationErrors()`: Flatten Zod errors into key-value pairs
- `validateField()`: Validate individual field values
- `debounce()`: Debounce async validation calls
- `calculatePasswordStrength()`: Password strength scoring
- `hasAsyncRefinements()`: Check if schema has async validations

## Dependencies

- `zod`: Schema validation
- `@hookform/resolvers`: Zod resolver for React Hook Form
- `react-hook-form`: Form state management

## Future Enhancements

- Localization/i18n integration for error messages
- Schema versioning for API compatibility
- Advanced async validation with caching
- Form persistence and recovery
- Accessibility improvements
- Testing utilities and examples
