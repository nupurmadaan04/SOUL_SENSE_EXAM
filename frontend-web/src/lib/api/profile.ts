import { apiClient } from './client';
import { ApiError } from './errors';
import { deduplicateRequest } from '../utils/requestUtils';

export interface PersonalProfile {
  first_name: string;
  last_name: string;
  age?: number;
  gender?: string;
  email?: string;
  occupation?: string;
  education_level?: string;
  bio?: string;
  avatar_path?: string;
  member_since?: string;
  eq_stats?: {
    last_score?: number;
    total_assessments?: number;
  };
}

export interface MedicalProfile {
  conditions?: string[];
  medications?: string[];
  mental_health_history?: string;
}

export interface UserSettings {
  theme?: 'light' | 'dark' | 'system';
  notifications_enabled?: boolean;
  email_notifications?: boolean;
  language?: string;
}

export interface UpdatePersonalProfile {
  first_name?: string;
  last_name?: string;
  age?: number;
  gender?: string;
  occupation?: string;
  education_level?: string;
}

export interface UpdateSettings {
  theme?: 'light' | 'dark' | 'system';
  notifications_enabled?: boolean;
  email_notifications?: boolean;
  language?: string;
}

export interface UserProfile {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  bio: string;
  age: number;
  gender: string;
  avatar_path: string;
  goals: {
    short_term: string;
    long_term: string;
  };
  preferences: {
    notification_frequency: string;
    theme: string;
  };
  created_at: string;
  updated_at: string;
  sleep_hours?: number;
  exercise_freq?: string;
  dietary_patterns?: string;
  has_therapist?: boolean;
  support_network_size?: number;
  primary_support_type?: string;
  primary_goal?: string;
  focus_areas?: string[];
  onboarding_completed?: boolean;
}

export interface UpdateUserProfile {
  first_name?: string;
  last_name?: string;
  bio?: string;
  age?: number;
  gender?: string;
  goals?: {
    short_term?: string;
    long_term?: string;
  };
  preferences?: {
    notification_frequency?: string;
    theme?: string;
  };
  sleep_hours?: number;
  exercise_freq?: string;
  dietary_patterns?: string;
  has_therapist?: boolean;
  support_network_size?: number;
  primary_support_type?: string;
  primary_goal?: string;
  focus_areas?: string[];
}

// ============================================================================
// Onboarding Types (Issue #933)
// ============================================================================

export interface OnboardingData {
  /** Step 1: Welcome & Vision */
  primary_goal?: string;
  focus_areas?: string[];
  
  /** Step 2: Current Lifestyle */
  sleep_hours?: number;
  exercise_freq?: string;
  dietary_patterns?: string;
  
  /** Step 3: Support System */
  has_therapist?: boolean;
  support_network_size?: number;
  primary_support_type?: string;
}

export interface OnboardingStatus {
  onboarding_completed: boolean;
}

export interface OnboardingCompleteResponse {
  message: string;
  onboarding_completed: boolean;
}

export const profileApi = {
  async getPersonalProfile(): Promise<PersonalProfile | null> {
    return deduplicateRequest('profile-personal', async () => {
      try {
        return await apiClient<PersonalProfile>('/profiles/personal');
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    });
  },

  async updatePersonalProfile(data: UpdatePersonalProfile): Promise<void> {
    return apiClient('/profiles/personal', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async getMedicalProfile(): Promise<MedicalProfile> {
    return deduplicateRequest('profile-medical', () => apiClient('/profiles/medical'));
  },

  async updateMedicalProfile(data: Partial<MedicalProfile>): Promise<void> {
    return apiClient('/profiles/medical', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async getSettings(): Promise<UserSettings> {
    return deduplicateRequest('profile-settings', async () => {
      try {
        return await apiClient<UserSettings>('/profiles/settings');
      } catch (error) {
        // Return defaults if the endpoint fails for any reason:
        // - 404: user hasn't created settings yet
        // - 500: backend model/schema mismatch
        // - Network error: server unreachable
        console.warn('[profileApi] getSettings failed, using defaults:', error);
        return {
          theme: 'system',
          notifications_enabled: true,
          email_notifications: true,
          language: 'en',
        };
      }
    });
  },

  async updateSettings(data: UpdateSettings): Promise<void> {
    return apiClient('/profiles/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async getUserProfile(): Promise<UserProfile> {
    return deduplicateRequest('profile-me', async () => {
      const data = await apiClient<any>('/users/me/complete');
      return {
        id: data.user.id,
        user_id: data.user.id,
        first_name: data.personal_profile?.first_name || '',
        last_name: data.personal_profile?.last_name || '',
        bio: data.personal_profile?.bio || '',
        age: data.personal_profile?.age || 0,
        gender: data.personal_profile?.gender || '',
        avatar_path: data.personal_profile?.avatar_path || '',
        goals: {
          short_term: data.strengths?.short_term_goals || '',
          long_term: data.strengths?.long_term_vision || '',
        },
        preferences: {
          notification_frequency: 'daily',
          theme: data.settings?.theme || 'system',
        },
        created_at: data.user.created_at,
        updated_at: data.personal_profile?.last_updated || data.user.created_at,
        sleep_hours: data.personal_profile?.sleep_hours,
        exercise_freq: data.personal_profile?.exercise_freq,
        dietary_patterns: data.personal_profile?.dietary_patterns,
        has_therapist: data.personal_profile?.has_therapist,
        support_network_size: data.personal_profile?.support_network_size,
        primary_support_type: data.personal_profile?.primary_support_type,
        primary_goal: data.strengths?.primary_goal,
        focus_areas: data.strengths?.focus_areas,
      };
    });
  },

  async updateUserProfile(data: UpdateUserProfile): Promise<UserProfile> {
    // 1. Update personal profile
    await apiClient('/profiles/personal', {
      method: 'PUT',
      body: JSON.stringify({
        first_name: data.first_name,
        last_name: data.last_name,
        bio: data.bio,
        age: data.age,
        gender: data.gender,
        sleep_hours: data.sleep_hours,
        exercise_freq: data.exercise_freq,
        dietary_patterns: data.dietary_patterns,
        has_therapist: data.has_therapist,
        support_network_size: data.support_network_size,
        primary_support_type: data.primary_support_type,
      }),
    });

    // 2. Update strengths
    const strengthsData: Record<string, any> = {};
    if (data.goals) {
      strengthsData.short_term_goals = data.goals.short_term;
      strengthsData.long_term_vision = data.goals.long_term;
    }
    if (data.primary_goal !== undefined) {
      strengthsData.primary_goal = data.primary_goal;
    }
    if (data.focus_areas !== undefined) {
      strengthsData.focus_areas = data.focus_areas;
    }
    if (Object.keys(strengthsData).length > 0) {
      await apiClient('/profiles/strengths', {
        method: 'PUT',
        body: JSON.stringify(strengthsData),
      });
    }

    // 3. Update settings
    if (data.preferences) {
      const settingsValidData: Record<string, any> = {};
      if (data.preferences.theme && ['light', 'dark'].includes(data.preferences.theme)) {
        settingsValidData.theme = data.preferences.theme;
      }
      if (Object.keys(settingsValidData).length > 0) {
        await apiClient('/profiles/settings', {
          method: 'PUT',
          body: JSON.stringify(settingsValidData),
        });
      }
    }

    return this.getUserProfile();
  },

  async uploadAvatar(file: File): Promise<{ avatar_path: string }> {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient('/users/me/avatar', {
      method: 'POST',
      body: formData,
    });
  },

  async deleteAvatar(): Promise<void> {
    return apiClient('/profiles/me/avatar', {
      method: 'DELETE',
    });
  },

  // ========================================================================
  // Onboarding API (Issue #933)
  // ========================================================================

  async getOnboardingStatus(): Promise<OnboardingStatus> {
    return apiClient<OnboardingStatus>('/users/me/onboarding/status');
  },

  async completeOnboarding(data: OnboardingData): Promise<OnboardingCompleteResponse> {
    return apiClient<OnboardingCompleteResponse>('/users/me/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // ========================================================================
  // Comprehensive Mental & Emotional Health Profile
  // ========================================================================

  async getMentalHealthProfile(): Promise<MentalHealthFullProfile> {
    const data = await apiClient<any>('/users/me/complete');
    return {
      sleep_hours: data.personal_profile?.sleep_hours ?? 7,
      exercise_freq: data.personal_profile?.exercise_freq ?? '2-3 times/week',
      dietary_patterns: data.personal_profile?.dietary_patterns ?? 'Balanced',
      has_therapist: data.personal_profile?.has_therapist ?? false,
      support_network_size: data.personal_profile?.support_network_size ?? 3,
      primary_support_type: data.personal_profile?.primary_support_type ?? 'Friends',
      daily_task_load: data.personal_profile?.daily_task_load ?? 5,
      occupation: data.personal_profile?.occupation ?? '',
      routine_habits: data.personal_profile?.routine_habits ?? 'Morning meditation, daily walks',
      primary_stressors: data.personal_profile?.primary_stressors ?? 'Deadlines, exam preparation',
      environment_type: data.personal_profile?.environment_type ?? 'Urban',
      recent_incidents: data.personal_profile?.recent_incidents ?? '',
      city: data.personal_profile?.city ?? '',
      country: data.personal_profile?.country ?? '',
      medications: data.medical_profile?.medications ?? '',
      conditions: data.medical_profile?.medical_conditions ?? data.medical_profile?.conditions ?? '',
      mental_health_history: data.medical_profile?.mental_health_history ?? '',
      preferred_tone: data.emotional_patterns?.preferred_tone ?? 'empathetic',
      common_emotions: data.emotional_patterns?.common_emotions ?? 'Calm, Focused, Occasional Stress',
      emotional_triggers: data.emotional_patterns?.emotional_triggers ?? 'Unclear expectations, sudden deadlines',
      coping_strategies: data.emotional_patterns?.coping_strategies ?? 'Deep breathing, music, journaling',
      primary_goal: data.strengths?.primary_goal ?? 'Enhance emotional regulation and clarity',
      focus_areas: data.strengths?.focus_areas ?? ['Self-Regulation', 'Empathy', 'Resilience'],
    };
  },

  async updateMentalHealthProfile(profile: MentalHealthFullProfile): Promise<void> {
    // 1. Personal profile update
    await apiClient('/profiles/personal', {
      method: 'PUT',
      body: JSON.stringify({
        sleep_hours: profile.sleep_hours,
        exercise_freq: profile.exercise_freq,
        dietary_patterns: profile.dietary_patterns,
        has_therapist: profile.has_therapist,
        support_network_size: profile.support_network_size,
        primary_support_type: profile.primary_support_type,
        daily_task_load: profile.daily_task_load,
        occupation: profile.occupation,
        routine_habits: profile.routine_habits,
        primary_stressors: profile.primary_stressors,
        environment_type: profile.environment_type,
        recent_incidents: profile.recent_incidents,
        city: profile.city,
        country: profile.country,
      }),
    });

    // 2. Medical profile update
    await apiClient('/profiles/medical', {
      method: 'PUT',
      body: JSON.stringify({
        medications: typeof profile.medications === 'string' ? profile.medications : JSON.stringify(profile.medications || []),
        medical_conditions: typeof profile.conditions === 'string' ? profile.conditions : JSON.stringify(profile.conditions || []),
        conditions: typeof profile.conditions === 'string' ? profile.conditions : JSON.stringify(profile.conditions || []),
        mental_health_history: profile.mental_health_history,
      }),
    });

    // 3. Emotional patterns update
    await apiClient('/profiles/emotional-patterns', {
      method: 'PUT',
      body: JSON.stringify({
        preferred_tone: profile.preferred_tone,
        common_emotions: typeof profile.common_emotions === 'string' ? profile.common_emotions : JSON.stringify(profile.common_emotions || []),
        emotional_triggers: profile.emotional_triggers,
        coping_strategies: profile.coping_strategies,
        preferred_support: profile.primary_support_type,
      }),
    });

    // 4. Strengths & goals update
    await apiClient('/profiles/strengths', {
      method: 'PUT',
      body: JSON.stringify({
        primary_goal: profile.primary_goal,
        focus_areas: profile.focus_areas,
      }),
    });
  },
};

export interface MentalHealthFullProfile {
  sleep_hours?: number;
  exercise_freq?: string;
  dietary_patterns?: string;
  has_therapist?: boolean;
  support_network_size?: number;
  primary_support_type?: string;
  daily_task_load?: number;
  occupation?: string;
  routine_habits?: string;
  primary_stressors?: string;
  environment_type?: string;
  recent_incidents?: string;
  city?: string;
  country?: string;
  medications?: string;
  conditions?: string;
  mental_health_history?: string;
  preferred_tone?: string;
  common_emotions?: string;
  emotional_triggers?: string;
  coping_strategies?: string;
  primary_goal?: string;
  focus_areas?: string[];
}

