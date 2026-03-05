'use client';

import { useState, useEffect } from 'react';
import { useDebounceCallback } from '@/hooks/useDebounceCallback';
import { Bell, Clock, ToggleLeft, ToggleRight, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';

interface ReminderSettingsProps {
  userId: number;
  onSettingsUpdated?: () => void;
}

interface ReminderSettings {
  daily_reminder_enabled: boolean;
  reminder_time: string;
  reminder_frequency: 'daily' | 'weekly' | 'custom';
  reminder_days?: string[];
  reminder_message?: string;
}

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function ReminderSettings({ userId, onSettingsUpdated }: ReminderSettingsProps) {
  const { toast } = useToast();
  const [settings, setSettings] = useState<ReminderSettings>({
    daily_reminder_enabled: false,
    reminder_time: '09:00',
    reminder_frequency: 'daily',
    reminder_days: DAYS_OF_WEEK,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Load current settings on mount
  useEffect(() => {
    loadReminderSettings();
  }, [userId]);

  const loadReminderSettings = async () => {
    try {
      const response = await fetch('/api/v1/notifications/reminders/settings', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load reminder settings');
      }

      const data = await response.json();
      setSettings({
        daily_reminder_enabled: data.daily_reminder_enabled || false,
        reminder_time: data.reminder_time || '09:00',
        reminder_frequency: data.reminder_frequency || 'daily',
        reminder_days: data.reminder_days || DAYS_OF_WEEK,
        reminder_message: data.reminder_message,
      });
    } catch (error) {
      console.error('Error loading reminder settings:', error);
      toast({
        title: 'Error',
        description: 'Failed to load reminder settings',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/v1/notifications/reminders/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        throw new Error('Failed to save reminder settings');
      }

      toast({
        title: 'Success',
        description: 'Reminder settings updated',
      });

      if (onSettingsUpdated) {
        onSettingsUpdated();
      }
    } catch (error) {
      console.error('Error saving reminder settings:', error);
      toast({
        title: 'Error',
        description: 'Failed to save reminder settings',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleReminder = (enabled: boolean) => {
    setSettings((prev) => ({
      ...prev,
      daily_reminder_enabled: enabled,
    }));
  };

  const handleTimeChange = (time: string) => {
    setSettings((prev) => ({
      ...prev,
      reminder_time: time,
    }));
  };

  const handleFrequencyChange = (frequency: 'daily' | 'weekly' | 'custom') => {
    setSettings((prev) => ({
      ...prev,
      reminder_frequency: frequency,
    }));
  };

  const handleDayToggle = (day: string) => {
    setSettings((prev) => {
      const days = prev.reminder_days || [];
      return {
        ...prev,
        reminder_days: days.includes(day) ? days.filter((d) => d !== day) : [...days, day],
      };
    });
  };

  const handleMessageChange = (message: string) => {
    setSettings((prev) => ({
      ...prev,
      reminder_message: message,
    }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Emotion Logging Reminders</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Get daily reminders to log your emotions. You can disable anytime.
        </p>
      </div>

      {/* Main Toggle */}
      <div className="flex items-center justify-between p-6 bg-muted/10 border border-border/40 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-background border border-border/40">
            {settings.daily_reminder_enabled ? (
              <ToggleRight className="h-6 w-6 text-primary" />
            ) : (
              <ToggleLeft className="h-6 w-6 text-muted-foreground" />
            )}
          </div>
          <div>
            <p className="font-semibold">Daily Reminders</p>
            <p className="text-sm text-muted-foreground">
              {settings.daily_reminder_enabled ? 'Enabled' : 'Disabled'}
            </p>
          </div>
        </div>
        <Checkbox
          checked={settings.daily_reminder_enabled}
          onChange={(e) => handleToggleReminder(e.target.checked)}
          className="h-6 w-6"
        />
      </div>

      {/* Settings (shown when enabled) */}
      {settings.daily_reminder_enabled && (
        <div className="space-y-6 border-t pt-6">
          {/* Reminder Time */}
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <Clock className="h-4 w-4" />
              Reminder Time
            </label>
            <div className="flex items-center gap-4">
              <input
                type="time"
                value={settings.reminder_time}
                onChange={(e) => handleTimeChange(e.target.value)}
                className="px-4 py-2 rounded-lg border border-border/40 bg-background h-10"
              />
              <span className="text-sm text-muted-foreground">
                You'll receive a reminder at this time in your timezone
              </span>
            </div>
          </div>

          {/* Frequency */}
          <div className="space-y-3">
            <label className="text-sm font-semibold">Frequency</label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {['daily', 'weekly', 'custom'].map((freq) => (
                <button
                  key={freq}
                  onClick={() => handleFrequencyChange(freq as 'daily' | 'weekly' | 'custom')}
                  className={`px-4 py-3 rounded-lg border border-border/40 text-sm font-medium transition-all ${
                    settings.reminder_frequency === freq
                      ? 'bg-primary/10 border-primary/40 text-primary'
                      : 'bg-muted/10 hover:border-border/60'
                  }`}
                >
                  {freq.charAt(0).toUpperCase() + freq.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Days of Week (for weekly) */}
          {settings.reminder_frequency === 'weekly' && (
            <div className="space-y-3">
              <label className="text-sm font-semibold">Days</label>
              <div className="grid grid-cols-4 gap-2">
                {DAYS_OF_WEEK.map((day) => (
                  <button
                    key={day}
                    onClick={() => handleDayToggle(day)}
                    className={`px-3 py-2 rounded-lg border border-border/40 text-sm font-medium transition-all ${
                      (settings.reminder_days || []).includes(day)
                        ? 'bg-primary/10 border-primary/40 text-primary'
                        : 'bg-muted/10 hover:border-border/60'
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Custom Message */}
          <div className="space-y-3">
            <label className="text-sm font-semibold">Custom Message (Optional)</label>
            <textarea
              value={settings.reminder_message || ''}
              onChange={(e) => handleMessageChange(e.target.value)}
              placeholder="Time to log your emotions"
              className="w-full px-4 py-2 rounded-lg border border-border/40 bg-background resize-none h-20"
            />
            <p className="text-xs text-muted-foreground">
              Leave empty to use the default message
            </p>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end pt-4">
        <Button
          onClick={handleSaveSettings}
          disabled={isSaving}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>

      {/* Info Card */}
      <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
        <p className="text-sm text-primary/80">
          <strong>Note:</strong> Reminders are sent at the specified time in your timezone. 
          You can disable reminders anytime by toggling the switch above.
        </p>
      </div>
    </div>
  );
}
