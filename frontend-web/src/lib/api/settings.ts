import { apiClient } from './client';

export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  notifications: {
    email: boolean;
    push: boolean;
    frequency: 'immediate' | 'daily' | 'weekly';
    types: {
      exam_reminders: boolean;
      journal_prompts: boolean;
      progress_updates: boolean;
      system_updates: boolean;
    };
  };
  privacy: {
    data_collection: boolean;
    analytics: boolean;
    data_retention_days: number;
    profile_visibility: 'public' | 'private' | 'friends';
    consent_ml_training: boolean;
    consent_aggregated_research: boolean;
    crisis_mode_enabled: boolean;
  };
  accessibility: {
    high_contrast: boolean;
    reduced_motion: boolean;
    font_size: 'small' | 'medium' | 'large';
  };
  account: {
    language: string;
    timezone: string;
    date_format: string;
  };
  ai_boundaries: {
    off_limit_topics: string[];
    ai_tone_preference: 'Clinical' | 'Warm' | 'Direct' | 'Philosophical';
    storage_retention_days: number;
  };
  onboarding_completed: boolean;
}

export const settingsApi = {
  async getSettings(): Promise<UserSettings> {
    try {
      return await apiClient<UserSettings>('/settings', { method: 'GET' });
    } catch (error) {
      // Return default settings if API fails
      return {
        theme: 'system',
        notifications: {
          email: true,
          push: true,
          frequency: 'daily',
          types: {
            exam_reminders: true,
            journal_prompts: true,
            progress_updates: true,
            system_updates: false,
          },
        },
        privacy: {
          data_collection: true,
          analytics: true,
          data_retention_days: 365,
          profile_visibility: 'private',
          consent_ml_training: false,
          consent_aggregated_research: false,
          crisis_mode_enabled: false,
        },
        accessibility: {
          high_contrast: false,
          reduced_motion: false,
          font_size: 'medium',
        },
        account: {
          language: 'en',
          timezone: 'UTC',
          date_format: 'MM/DD/YYYY',
        },
        ai_boundaries: {
          off_limit_topics: [],
          ai_tone_preference: 'Warm',
          storage_retention_days: 180,
        },
        onboarding_completed: false,
      };
    }
  },

  async updateSettings(updates: Partial<UserSettings>): Promise<UserSettings> {
    try {
      return await apiClient<UserSettings>('/settings', {
        method: 'PUT',
        body: JSON.stringify(updates),
      });
    } catch (error) {
      throw new Error('Failed to update settings');
    }
  },

  async syncSettings(): Promise<UserSettings> {
    try {
      return await apiClient<UserSettings>('/settings/sync', { method: 'POST' });
    } catch (error) {
      throw new Error('Failed to sync settings');
    }
  },
};
