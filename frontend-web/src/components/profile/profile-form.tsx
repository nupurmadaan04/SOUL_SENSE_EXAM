'use client';

import React, { useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { motion } from 'framer-motion';
import { Camera, Loader2, User, ChevronRight, Save } from 'lucide-react';
import {
  Button,
  Input,
  Textarea,
  Avatar,
  AvatarImage,
  AvatarFallback,
  Select,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui';
import { FormField } from '@/components/forms';
import { cn } from '@/lib/utils';
import { UserProfile } from '@/lib/api/profile';

// TagInput Component
function TagInput({
  value,
  onChange,
  placeholder,
  ...props
}: {
  value?: string[];
  onChange?: (value: string[]) => void;
  placeholder?: string;
  [key: string]: any;
}) {
  const [inputValue, setInputValue] = useState('');
  const safeList = Array.isArray(value) ? value : [];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault();
      const newValue = [...safeList, inputValue.trim()];
      onChange?.(newValue);
      setInputValue('');
    } else if (e.key === 'Backspace' && !inputValue && safeList.length) {
      const newValue = safeList.slice(0, -1);
      onChange?.(newValue);
    }
  };

  const removeTag = (index: number) => {
    const newValue = safeList.filter((_, i) => i !== index);
    onChange?.(newValue);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 min-h-[2.5rem] p-2 border border-input rounded-md bg-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
        {safeList.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-primary/10 text-primary rounded-md"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              className="hover:text-destructive"
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={value?.length ? '' : placeholder}
          className="flex-1 min-w-[120px] bg-transparent outline-none text-sm"
          {...props}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Press Enter to add a tag, Backspace to remove the last tag
      </p>
    </div>
  );
}

// Zod Schema for validation
const profileSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  bio: z.string().max(500, 'Bio must be less than 500 characters').optional(),
  age: z.coerce.number().min(13, 'Age must be at least 13').max(120, 'Age must be less than 120'),
  gender: z.enum(['male', 'female', 'other', 'prefer_not_to_say']),
  shortTermGoals: z.string().optional(),
  longTermGoals: z.string().optional(),
  avatarUrl: z.string().optional(),
  sleepHours: z.coerce.number().min(0, 'Sleep hours must be at least 0').max(24, 'Sleep hours must be at most 24').optional(),
  exerciseFrequency: z.enum(['none', 'light', 'moderate', 'heavy']).optional(),
  dietType: z.string().optional(),
  hasTherapist: z.boolean().optional(),
  supportNetworkSize: z.coerce.number().min(0, 'Network size must be at least 0').max(100, 'Network size must be at most 100').optional(),
  primarySupportType: z.enum(['family', 'friends', 'professional', 'none']).optional(),
  primaryGoal: z.string().max(500, 'Primary goal must be less than 500 characters').optional(),
  focusAreas: z.array(z.string()).optional(),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;

interface ProfileFormProps {
  profile?: Partial<UserProfile>;
  onSubmit: (data: ProfileFormValues & { avatarFile?: File }) => void;
  onCancel?: () => void;
  isSubmitting?: boolean;
}

/**
 * ProfileForm Component
 *
 * An editable form for updating user profile information.
 * Features:
 * - Avatar upload with instant preview
 * - Field validation with react-hook-form and zod
 * - Responsive layout with Framer Motion animations
 * - Character count for bio
 */
export function ProfileForm({ profile, onSubmit, onCancel, isSubmitting }: ProfileFormProps) {
  const [avatarPreview, setAvatarPreview] = useState<string | null>(profile?.avatar_path || null);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      firstName: profile?.first_name || '',
      lastName: profile?.last_name || '',
      bio: profile?.bio || '',
      age: profile?.age || 18,
      gender: (profile?.gender as 'male' | 'female' | 'other' | 'prefer_not_to_say') || 'prefer_not_to_say',
      shortTermGoals: profile?.goals?.short_term || '',
      longTermGoals: profile?.goals?.long_term || '',
      sleepHours: profile?.sleep_hours,
      exerciseFrequency: profile?.exercise_freq as 'none' | 'light' | 'moderate' | 'heavy',
      dietType: profile?.dietary_patterns || '',
      hasTherapist: profile?.has_therapist,
      supportNetworkSize: profile?.support_network_size,
      primarySupportType: profile?.primary_support_type as 'family' | 'friends' | 'professional' | 'none',
      primaryGoal: profile?.primary_goal || '',
      focusAreas: Array.isArray(profile?.focus_areas)
        ? profile.focus_areas
        : typeof profile?.focus_areas === 'string'
        ? profile.focus_areas.split(',').map((s: string) => s.trim()).filter(Boolean)
        : [],
    },
  });

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const onFormSubmit = (data: ProfileFormValues) => {
    onSubmit({ ...data, avatarFile: avatarFile || undefined });
  };

  return (
    <Card className="max-w-3xl mx-auto border border-border/40 backdrop-blur-md bg-background/60 overflow-hidden shadow-sm">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <form onSubmit={form.handleSubmit(onFormSubmit)}>
          <CardHeader className="text-center border-b border-border/40 bg-muted/10 pb-10">
            <CardTitle className="text-3xl font-black tracking-tight">Edit Profile</CardTitle>
            <CardDescription className="text-muted-foreground mt-2 font-medium">
              Update your personal identity and professional aspirations.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-10 pt-10 px-8">
            {/* Avatar Section */}
            <div className="flex flex-col items-center justify-center space-y-6">
              <div className="relative group cursor-pointer" onClick={handleAvatarClick}>
                <Avatar className="h-32 w-32 border-4 border-background transition-all duration-300 group-hover:border-primary/30 shadow-xl overflow-hidden">
                  <AvatarImage src={avatarPreview || undefined} className="object-cover" />
                  <AvatarFallback className="bg-muted">
                    <User className="h-14 w-14 text-muted-foreground/50" />
                  </AvatarFallback>
                </Avatar>
                <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <Camera className="text-white h-8 w-8" />
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept="image/*"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAvatarClick}
                className="text-[10px] font-black uppercase tracking-widest px-6 h-9 rounded-full border-border/60 hover:bg-primary/5 hover:text-primary transition-colors"
              >
                Change Avatar
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="firstName"
                label="First Name"
                required
                placeholder="E.g. John"
              />
              <FormField
                control={form.control}
                name="lastName"
                label="Last Name"
                required
                placeholder="E.g. Doe"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="age"
                label="Age"
                type="number"
                required
                placeholder="18"
              />
              <FormField control={form.control} name="gender" label="Gender" required>
                {(field) => (
                  <Select {...field}>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </Select>
                )}
              </FormField>
            </div>

            <FormField
              control={form.control}
              name="bio"
              label="Bio (Max 500 chars)"
              placeholder="Tell us about yourself..."
            >
              {(field) => (
                <div className="relative">
                  <Textarea
                    {...field}
                    rows={4}
                    className="resize-none pr-12 focus:ring-primary/30"
                    maxLength={500}
                  />
                  <span
                    className={cn(
                      'absolute bottom-2 right-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-background/50 backdrop-blur-sm border border-border/50',
                      (field.value?.length || 0) > 450
                        ? 'text-destructive font-bold'
                        : 'text-muted-foreground'
                    )}
                  >
                    {field.value?.length || 0}/500
                  </span>
                </div>
              )}
            </FormField>

            <div className="space-y-6 pt-6 border-t border-border/50">
              <h3 className="text-lg font-semibold flex items-center text-foreground/80">
                <ChevronRight className="h-5 w-5 mr-1 text-primary" />
                Progress & Goals
              </h3>

              <div className="grid grid-cols-1 gap-6">
                <FormField
                  control={form.control}
                  name="shortTermGoals"
                  label="Short-term Goals"
                  placeholder="What do you want to achieve in the next few weeks?"
                >
                  {(field) => <Textarea {...field} rows={3} className="resize-none shadow-sm" />}
                </FormField>

                <FormField
                  control={form.control}
                  name="longTermGoals"
                  label="Long-term Goals"
                  placeholder="What are your big aspirations for the future?"
                >
                  {(field) => <Textarea {...field} rows={3} className="resize-none shadow-sm" />}
                </FormField>
              </div>
            </div>

            <div className="space-y-6 pt-6 border-t border-border/50">
              <h3 className="text-lg font-semibold flex items-center text-foreground/80">
                <ChevronRight className="h-5 w-5 mr-1 text-primary" />
                Lifestyle & Habits
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="sleepHours"
                  label="Average Sleep Hours per Night"
                  type="number"
                  step="0.5"
                  placeholder="7.5"
                />
                <FormField control={form.control} name="exerciseFrequency" label="Exercise Frequency" required>
                  {(field) => (
                    <Select {...field}>
                      <option value="">Select frequency</option>
                      <option value="none">None</option>
                      <option value="light">Light (1-2 times/week)</option>
                      <option value="moderate">Moderate (3-4 times/week)</option>
                      <option value="heavy">Heavy (5+ times/week)</option>
                    </Select>
                  )}
                </FormField>
              </div>

              <FormField
                control={form.control}
                name="dietType"
                label="Diet Type"
                placeholder="E.g. Mediterranean, Vegetarian, Keto..."
              />
            </div>

            <div className="space-y-6 pt-6 border-t border-border/50">
              <h3 className="text-lg font-semibold flex items-center text-foreground/80">
                <ChevronRight className="h-5 w-5 mr-1 text-primary" />
                Support System
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField control={form.control} name="hasTherapist" label="Has Therapist">
                  {(field) => (
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="hasTherapist"
                        {...field}
                        checked={field.value || false}
                        className="rounded border-border/40"
                      />
                      <label htmlFor="hasTherapist" className="text-sm font-medium">
                        I have access to a therapist
                      </label>
                    </div>
                  )}
                </FormField>
                <FormField
                  control={form.control}
                  name="supportNetworkSize"
                  label="Support Network Size"
                  type="number"
                  placeholder="0"
                />
              </div>

              <FormField control={form.control} name="primarySupportType" label="Primary Support Type">
                {(field) => (
                  <Select {...field}>
                    <option value="">Select support type</option>
                    <option value="family">Family</option>
                    <option value="friends">Friends</option>
                    <option value="professional">Professional</option>
                    <option value="none">None</option>
                  </Select>
                )}
              </FormField>
            </div>

            <div className="space-y-6 pt-6 border-t border-border/50">
              <h3 className="text-lg font-semibold flex items-center text-foreground/80">
                <ChevronRight className="h-5 w-5 mr-1 text-primary" />
                Goals & Vision
              </h3>

              <FormField
                control={form.control}
                name="primaryGoal"
                label="Primary Goal"
                placeholder="What is your main objective or vision for personal growth?"
              >
                {(field) => (
                  <div className="relative">
                    <Textarea
                      {...field}
                      rows={4}
                      className="resize-none pr-12 focus:ring-primary/30"
                      maxLength={500}
                    />
                    <span
                      className={cn(
                        'absolute bottom-2 right-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-background/50 backdrop-blur-sm border border-border/50',
                        (field.value?.length || 0) > 450
                          ? 'text-destructive font-bold'
                          : 'text-muted-foreground'
                      )}
                    >
                      {field.value?.length || 0}/500
                    </span>
                  </div>
                )}
              </FormField>

              <FormField
                control={form.control}
                name="focusAreas"
                label="Focus Areas"
                placeholder="Add areas you want to focus on (press Enter to add)"
              >
                {(field) => <TagInput {...field} />}
              </FormField>
            </div>

          </CardContent>

          <CardFooter className="pt-6 pb-8 flex justify-end gap-3 bg-muted/10 border-t border-border/50">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={onCancel}
                disabled={isSubmitting}
                className="px-6 font-semibold"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              size="lg"
              disabled={isSubmitting}
              className="px-10 font-bold transition-all hover:shadow-primary/25 hover:shadow-xl active:scale-[0.98]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </motion.div>
    </Card>
  );
}
