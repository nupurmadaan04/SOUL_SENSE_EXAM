'use client';

import React from 'react';
import { useForm, UseFormProps, FieldValues, UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { toast } from 'sonner';

interface FormProps<T extends FieldValues> extends Omit<UseFormProps<T>, 'defaultValues'> {
  schema: z.ZodSchema<T>;
  onSubmit: (data: T, methods: UseFormReturn<T>) => void | Promise<void>;
  children: (methods: UseFormReturn<T>) => React.ReactNode;
  className?: string;
  defaultValues?: Partial<T>;
}

export function Form<T extends FieldValues>({
  schema,
  onSubmit,
  children,
  className = '',
  defaultValues,
  ...formOptions
}: FormProps<T>) {
  const methods = useForm<T>({
    ...formOptions,
    resolver: zodResolver(schema),
    defaultValues: defaultValues as any,
  });

  const handleSubmit = methods.handleSubmit(
    async (data) => {
      try {
        await onSubmit(data, methods);
      } catch (error) {
        console.error('Form submission error:', error);
      }
    },
    (errors) => {
      console.warn('Form validation errors on submit:', errors);
      const errorEntries = Object.entries(errors);
      if (errorEntries.length > 0) {
        const [field, err] = errorEntries[0];
        const msg = (err as any)?.message || `Please check the ${field} field.`;
        toast.error(String(msg));
      }
    }
  );

  return (
    <form onSubmit={handleSubmit} className={className}>
      {children(methods)}
    </form>
  );
}
