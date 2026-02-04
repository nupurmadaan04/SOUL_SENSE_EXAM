'use client';

import React from 'react';
import { useController, Control, FieldValues, Path } from 'react-hook-form';
import { FormLabel } from './FormLabel';
import { FormError } from './FormError';
import { FormMessage } from './FormMessage';
import { Input } from '@/components/ui';
import { cn } from '@/lib/utils';

interface FormFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label?: string;
  placeholder?: string;
  type?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  children?: (field: any) => React.ReactNode;
}

export function FormField<T extends FieldValues>({
  control,
  name,
  label,
  placeholder,
  type = 'text',
  required = false,
  disabled = false,
  className = '',
  children,
}: FormFieldProps<T>) {
  const {
    field,
    fieldState: { error },
  } = useController({
    name,
    control,
  });

  // Add error styling class when field has error
  const inputClassName = cn(
    className,
    error && 'border-destructive focus-visible:ring-destructive'
  );

  const fieldProps = {
    ...field,
    placeholder,
    type,
    required,
    disabled,
    className: inputClassName,
    'aria-invalid': !!error,
    'aria-describedby': error ? `${name}-error` : undefined,
  };

  return (
    <div className={cn('space-y-2', className)}>
      {label && (
        <FormLabel htmlFor={name} required={required}>
          {label}
        </FormLabel>
      )}
      {children ? children(fieldProps) : <Input {...fieldProps} />}
      <FormError error={error?.message} />
      <FormMessage name={name} />
    </div>
  );
}

