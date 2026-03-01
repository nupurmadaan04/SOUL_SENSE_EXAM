import { apiClient } from './client';

export interface UserPreferences {
    email_notifications: boolean;
    weekly_digest: boolean;
    assessment_frequency_days: 7 | 14 | 30;
    dark_mode_preference: boolean;
}

export const preferencesApi = {
    async getPreferences(): Promise<UserPreferences> {
        try {
            return await apiClient<UserPreferences>('/users/preferences', {
                method: 'GET',
            });
        } catch (error) {
            console.warn('Failed to fetch user preferences, using defaults:', error);
            return {
                email_notifications: false,
                weekly_digest: false,
                assessment_frequency_days: 14,
                dark_mode_preference: false,
            };
        }
    },

    async updatePreferences(preferences: Partial<UserPreferences>): Promise<UserPreferences> {
        return apiClient<UserPreferences>('/users/preferences', {
            method: 'PATCH',
            body: JSON.stringify(preferences),
        });
    },
};
