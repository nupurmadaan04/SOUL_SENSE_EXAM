'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useProfile } from '@/hooks/useProfile';
import { ProfileCard, ProfileForm } from '@/components/profile';
import { Button } from '@/components/ui';
import { Card, CardContent } from '@/components/ui';
import { Skeleton } from '@/components/ui';
import { motion, AnimatePresence } from 'framer-motion';
import { resultsApi } from '@/lib/api/results';
import { journalApi } from '@/lib/api/journal';

import { Calendar, Target, BookOpen, Trophy, User as UserIcon, Settings } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuth();
  const { profile, isLoading: loading, error, updateProfile, refetch } = useProfile();
  const [isEditing, setIsEditing] = useState(false);

  const { data: examHistory } = useQuery({
    queryKey: ['profile', 'exam-history'],
    queryFn: () => resultsApi.getHistory(1, 1),
  });

  const { data: journalAnalytics } = useQuery({
    queryKey: ['profile', 'journal-analytics'],
    queryFn: () => journalApi.getAnalytics(),
  });

  const handleEditToggle = () => {
    setIsEditing(!isEditing);
  };

  const handleSave = async (data: any) => {
    // Transform camelCase to snake_case for API
    const transformedData = {
      first_name: data.firstName,
      last_name: data.lastName,
      bio: data.bio,
      age: data.age,
      gender: data.gender,
      goals: {
        short_term: data.shortTermGoals,
        long_term: data.longTermGoals,
      },
      sleep_hours: data.sleepHours,
      exercise_freq: data.exerciseFrequency,
      dietary_patterns: data.dietType,
      has_therapist: data.hasTherapist,
      support_network_size: data.supportNetworkSize,
      primary_support_type: data.primarySupportType,
      primary_goal: data.primaryGoal,
      focus_areas: data.focusAreas,
    };
    await updateProfile(transformedData);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-12 px-6 space-y-10">
        <Skeleton className="h-48 w-full rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Skeleton className="h-64 rounded-2xl" />
          <Skeleton className="h-64 md:col-span-2 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-12 px-6">
        <div className="text-center bg-destructive/5 p-12 rounded-2xl border border-destructive/10">
          <p className="text-destructive font-bold mb-6 text-lg">
            Failed to load profile: {typeof error === 'string' ? error : (error as any)?.message || 'Unknown error'}
          </p>
          <Button onClick={refetch} variant="outline" className="font-bold">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-12 px-6 space-y-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-4xl font-black tracking-tight text-foreground">Profile</h1>
          <p className="text-muted-foreground font-medium opacity-70">
            Manage your personal identity and track your growth journey.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        {/* Profile Section */}
        <div className="lg:col-span-8">
          <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm overflow-hidden h-full">
            <CardContent className="p-8 md:p-10">
              <AnimatePresence mode="wait">
                {!isEditing ? (
                  <motion.div
                    key="view"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                  >
                    <ProfileCard
                      profile={profile}
                      user={user}
                      variant="full"
                      editable={true}
                      onEdit={handleEditToggle}
                      onAvatarUpdated={refetch}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="edit"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="space-y-8">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <h2 className="text-2xl font-black">Edit Profile</h2>
                          <p className="text-sm text-muted-foreground font-medium">
                            Update your profile settings
                          </p>
                        </div>
                        <Button
                          onClick={handleCancel}
                          variant="ghost"
                          size="sm"
                          className="font-bold text-muted-foreground"
                        >
                          Cancel
                        </Button>
                      </div>
                      <ProfileForm
                        profile={(profile as any) || undefined}
                        onSubmit={handleSave}
                        onCancel={handleCancel}
                        isSubmitting={loading}
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>
        </div>

        {/* Stats Section */}
        <div className="lg:col-span-4 space-y-8">
          {/* Member Since Card */}
          <Card className="rounded-3xl border-none bg-primary text-primary-foreground shadow-lg overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
            <CardContent className="p-8 relative">
              <div className="flex items-center gap-3 mb-6 opacity-80 uppercase tracking-widest font-black text-[10px]">
                <Calendar className="h-4 w-4" />
                <span>Member Since</span>
              </div>
              <p className="text-3xl font-black">
                {user?.created_at
                  ? new Date(user.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      year: 'numeric',
                    })
                  : 'February 2026'}
              </p>
            </CardContent>
          </Card>

          {/* Stats Cards Grid */}
          <div className="grid grid-cols-1 gap-4">
            <div className="flex items-center gap-4 p-5 rounded-2xl bg-background/60 backdrop-blur-md border border-border/40 hover:border-primary/20 transition-all group">
              <div className="p-3 rounded-xl bg-primary/5 text-primary">
                <Target className="h-5 w-5" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Total Assessments
                </p>
                <p className="text-xl font-black">{examHistory?.total || 0}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-5 rounded-2xl bg-background/60 backdrop-blur-md border border-border/40 hover:border-primary/20 transition-all group">
              <div className="p-3 rounded-xl bg-emerald-500/5 text-emerald-600">
                <BookOpen className="h-5 w-5" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Journal Reflections
                </p>
                <p className="text-xl font-black">{journalAnalytics?.total_entries || 0}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-5 rounded-2xl bg-background/60 backdrop-blur-md border border-border/40 hover:border-primary/20 transition-all group">
              <div className="p-3 rounded-xl bg-amber-500/5 text-amber-600">
                <Trophy className="h-5 w-5" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/60 mb-0.5">
                  Current Streak
                </p>
                <p className="text-xl font-black">{journalAnalytics?.streak_days || 0} Days</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
