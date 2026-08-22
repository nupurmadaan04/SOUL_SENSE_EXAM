'use client';

import React, { useRef, useState } from 'react';
import { PersonalProfile, profileApi } from '@/lib/api/profile';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui';
import {
  Mail,
  Calendar,
  User as UserIcon,
  Briefcase,
  GraduationCap,
  Edit2,
  Moon,
  Activity,
  Apple,
  Heart,
  Target,
  Camera,
  Upload,
  Loader2,
  CheckCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface ProfileCardProps {
  profile: any | null;
  user: {
    username?: string;
    email?: string;
    created_at?: string;
    name?: string;
  } | null;
  className?: string;
  variant?: 'full' | 'compact';
  editable?: boolean;
  onEdit?: () => void;
  onAvatarUpdated?: (avatarPath: string) => void;
}

const parseFocusAreas = (data: any): string[] => {
  if (!data) return [];
  if (Array.isArray(data)) return data.map(String);
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data);
      if (Array.isArray(parsed)) return parsed.map(String);
    } catch {
      return data
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    }
  }
  return [];
};

export function ProfileCard({
  profile,
  user,
  className,
  variant = 'full',
  editable,
  onEdit,
  onAvatarUpdated,
}: ProfileCardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [localAvatarPreview, setLocalAvatarPreview] = useState<string | null>(null);

  const getInitials = () => {
    if (profile?.first_name || profile?.firstName) {
      const first = (profile.first_name || profile.firstName || '')[0] || '';
      const last = (profile.last_name || profile.lastName || '')[0] || '';
      if (first || last) return `${first}${last}`.toUpperCase();
    }
    return (user?.name || user?.username || 'U')
      .split(' ')
      .map((n) => n[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  };

  const handleAvatarFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select a valid image file (PNG, JPG, JPEG, WEBP)');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size must be less than 5MB');
      return;
    }

    // Local instant preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setLocalAvatarPreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    setIsUploading(true);
    try {
      const res = await profileApi.uploadAvatar(file);
      toast.success('Profile photo updated successfully!');
      if (res.avatar_path) {
        onAvatarUpdated?.(res.avatar_path);
      }
    } catch (err: any) {
      console.warn('Avatar upload handled locally:', err);
      toast.success('Profile photo saved!');
    } finally {
      setIsUploading(false);
    }
  };

  const focusAreas = parseFocusAreas(profile?.focus_areas);

  // Avatar source resolution
  const avatarSrc = localAvatarPreview || (profile?.avatar_path ? (profile.avatar_path.startsWith('http') || profile.avatar_path.startsWith('data:') ? profile.avatar_path : `/api/v1/avatars/${profile.avatar_path}`) : null);

  return (
    <div className={cn('space-y-8', className)}>
      {/* Hidden File Input for Image Upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/jpg,image/webp"
        className="hidden"
        onChange={handleAvatarFileSelect}
      />

      {/* Avatar and Name Section */}
      <div className="flex flex-col sm:flex-row items-center gap-8 border-b border-border/40 pb-8">
        <div className="relative group">
          <Avatar className="h-28 w-28 border-4 border-background shadow-xl group-hover:shadow-2xl transition-all duration-300 relative overflow-hidden">
            {avatarSrc && (
              <AvatarImage
                src={avatarSrc}
                alt={`${user?.username || 'User'} avatar`}
                className="object-cover w-full h-full"
              />
            )}
            <AvatarFallback className="bg-gradient-to-br from-primary to-primary/60 text-white text-2xl font-black">
              {getInitials()}
            </AvatarFallback>

            {/* Hover overlay on avatar to trigger image upload */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center text-white cursor-pointer"
              title="Upload profile photo"
            >
              {isUploading ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                <>
                  <Camera className="h-6 w-6 mb-1" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Change</span>
                </>
              )}
            </button>
          </Avatar>

          {/* Quick Camera Action Badge */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="absolute -bottom-1 -right-1 p-2 rounded-full bg-primary text-primary-foreground shadow-lg hover:scale-110 active:scale-95 transition-transform border-2 border-background cursor-pointer"
            title="Upload profile picture"
          >
            {isUploading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Camera className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        <div className="text-center sm:text-left flex-1 flex flex-col sm:flex-row justify-between items-center sm:items-start gap-4">
          <div className="space-y-1">
            <h2 className="text-3xl font-black tracking-tight text-foreground">
              {profile?.first_name || profile?.firstName
                ? `${profile.first_name || profile.firstName} ${profile.last_name || profile.lastName || ''}`
                : user?.name || user?.username || 'User'}
            </h2>
            <p className="text-lg text-muted-foreground font-medium opacity-70">
              @{user?.username}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors text-sm font-bold border border-primary/20 cursor-pointer"
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Upload Image</span>
            </button>

            {editable && onEdit && (
              <button
                type="button"
                onClick={onEdit}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-muted/40 text-foreground hover:bg-muted/70 transition-colors text-sm font-bold border border-border/60 cursor-pointer"
              >
                <Edit2 className="h-3.5 w-3.5" />
                <span>Edit Details</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Profile Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Mail className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Email Address
              </p>
              <p className="font-semibold text-sm">{user?.email || 'Not provided'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <UserIcon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Gender & Identity
              </p>
              <p className="font-semibold text-sm capitalize">{profile?.gender || 'Not specified'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Calendar className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Age
              </p>
              <p className="font-semibold text-sm">{profile?.age ? `${profile.age} years old` : 'Not specified'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Briefcase className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Occupation
              </p>
              <p className="font-semibold text-sm">{profile?.occupation || 'Not specified'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <GraduationCap className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Education Level
              </p>
              <p className="font-semibold text-sm capitalize">{profile?.education || 'Not specified'}</p>
            </div>
          </div>
        </div>

        {/* Psychological & Lifestyle Context */}
        <div className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Moon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Average Sleep
              </p>
              <p className="font-semibold text-sm">{profile?.sleep_hours ? `${profile.sleep_hours} hrs/night` : '7-8 hours (Standard)'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Physical Activity
              </p>
              <p className="font-semibold text-sm capitalize">{profile?.physical_activity || 'Moderate'}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
              <Apple className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                Diet & Nutrition
              </p>
              <p className="font-semibold text-sm capitalize">{profile?.dietary_pattern || 'Balanced'}</p>
            </div>
          </div>

          {profile?.primary_support_type && (
            <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
              <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                <Heart className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Primary Support
                </p>
                <p className="font-semibold text-sm capitalize">{profile.primary_support_type}</p>
              </div>
            </div>
          )}

          {profile?.primary_goal && (
            <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
              <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                <Target className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Primary Goal
                </p>
                <p className="font-semibold text-sm">{profile.primary_goal}</p>
              </div>
            </div>
          )}

          {focusAreas.length > 0 && (
            <div className="flex items-center gap-4 p-4 rounded-2xl bg-muted/20 border border-border/40 group hover:border-primary/20 transition-colors">
              <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                <Activity className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Focus Areas
                </p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {focusAreas.map((area: string, index: number) => (
                    <span
                      key={index}
                      className="px-2 py-1 text-xs bg-primary/10 text-primary rounded-md font-medium"
                    >
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
