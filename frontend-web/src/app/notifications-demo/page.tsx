'use client';

import { useState } from 'react';
import { NotificationSettings } from '@/components/settings';
import { UserSettings } from '@/lib/api/settings';

export default function NotificationsDemoPage() {
  const [settings, setSettings] = useState<UserSettings>({
    onboarding_completed: true,
    theme: 'system',
    notifications: {
      email: true,
      push: false,
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
      date_format: 'MM/dd/yyyy',
    },
    ai_boundaries: {
      off_limit_topics: [],
      ai_tone_preference: 'Warm',
      storage_retention_days: 365,
    },
  });

  const handleSettingsChange = (updated: Partial<UserSettings>) => {
    setSettings((prev: UserSettings) => ({ ...prev, ...updated }));
  };

  return (
    <div className="min-h-screen bg-background py-12 px-4">
      <div className="max-w-4xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-extrabold tracking-tight">Notification Settings Demo</h1>
          <p className="text-muted-foreground text-lg">
            Testing the Notification Preferences interface
          </p>
        </div>

        <div className="bg-card p-6 rounded-3xl border shadow-2xl">
          <NotificationSettings settings={settings} onChange={handleSettingsChange} />
        </div>

        <div className="bg-muted p-6 rounded-2xl border">
          <h3 className="font-bold mb-4">Current State Debug:</h3>
          <pre className="text-xs bg-black text-green-400 p-4 rounded overflow-auto">
            {JSON.stringify(settings, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
