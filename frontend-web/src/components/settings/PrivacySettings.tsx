'use client';

import { useState } from 'react';
import { UserSettings } from '../../lib/api/settings';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui';
import { Checkbox } from '@/components/ui';
import { Button } from '@/components/ui';
import { useDebounceCallback } from '@/hooks/useDebounceCallback';
import {
  AlertTriangle,
  Download,
  Trash2,
  Shield,
  Activity,
  Database,
  Eye,
  ShieldCheck,
  Lock,
  Loader2,
} from 'lucide-react';

import { useToast } from '@/lib/toast';
import { apiClient } from '@/lib/api/client';

interface PrivacySettingsProps {
  settings: UserSettings;
  onChange: (updates: Partial<UserSettings>) => void;
}

export function PrivacySettings({ settings, onChange }: PrivacySettingsProps) {
  const { toast } = useToast();
  const [isDownloading, setIsDownloading] = useState(false);
  const debouncedOnChange = useDebounceCallback(onChange, 500);

  const handlePrivacyChange = (key: 'data_collection' | 'analytics', value: boolean) => {
    debouncedOnChange({
      privacy: {
        ...settings.privacy,
        [key]: value,
      },
    });
  };

  const handleRetentionChange = (days: number) => {
    debouncedOnChange({
      privacy: {
        ...settings.privacy,
        data_retention_days: days,
      },
    });
  };

  const handleConsentChange = (key: 'consent_ml_training' | 'consent_aggregated_research', value: boolean) => {
    debouncedOnChange({
      privacy: {
        ...settings.privacy,
        [key]: value,
      },
    });
  };

  const handleVisibilityChange = (value: string) => {
    debouncedOnChange({
      privacy: {
        ...settings.privacy,
        profile_visibility: value as 'private' | 'friends' | 'public',
      },
    });
  };

  const handleCrisisModeChange = async (value: boolean) => {
    try {
      // Update immediately via API
      await apiClient('/profiles/crisis_settings', {
        method: 'PATCH',
        body: JSON.stringify({
          crisis_mode_enabled: value,
        }),
      });

      // Update local state
      onChange({
        privacy: {
          ...settings.privacy,
          crisis_mode_enabled: value,
        },
      });

      toast({
        type: 'success',
        message: `Crisis support ${value ? 'enabled' : 'disabled'} successfully.`,
      });
    } catch (error) {
      console.error('Failed to update crisis mode:', error);
      toast({
        type: 'error',
        message: 'Failed to update crisis support setting.',
      });
    }
  };

  const handleExportData = async () => {
    try {
      setIsDownloading(true);

      // Explicitly require 'blob' translation from fetch/apiClient
      const response = await apiClient.get<Blob>('/reports/export/pdf', {
        responseType: 'blob',
      });

      // Synthesize the Blob into a temporary geometric URL
      const blob = new Blob([response], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Read explicit filename boundary or manufacture one generically
      const contentDate = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `SoulSense_Report_${contentDate}.pdf`);

      // Mount, trigger physical browser payload, wipe clean
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({
        type: 'success',
        message: 'Your report has been generated and downloaded.',
      });
    } catch (error) {
      console.error('PDF Export Error:', error);
      toast({
        type: 'error',
        message: 'Critically failed to initialize API PDF extraction.',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDeleteAccount = () => {
    console.log('Deleting account...');
  };

  return (
    <div className="space-y-12">
      {/* Data Stewardship */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <ShieldCheck className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Data Stewardship</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground">
                <Activity className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-bold">Analytics Sharing</p>
                <p className="text-[10px] text-muted-foreground font-medium">
                  Help improve Soul Sense with usage data
                </p>
              </div>
            </div>
            <Checkbox
              checked={settings.privacy.analytics}
              onChange={(e) => handlePrivacyChange('analytics', e.target.checked)}
              className="h-6 w-6 rounded-lg border-2 border-border/60"
            />
          </div>

          <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground">
                <Database className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-bold">Collection Protocols</p>
                <p className="text-[10px] text-muted-foreground font-medium">
                  Allow personalization through data capture
                </p>
              </div>
            </div>
            <Checkbox
              checked={settings.privacy.data_collection}
              onChange={(e) => handlePrivacyChange('data_collection', e.target.checked)}
              className="h-6 w-6 rounded-lg border-2 border-border/60"
            />
          </div>
        </div>
      </div>

      {/* Data Consent */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Shield className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Data Consent</h3>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground">
                <Database className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-bold">Allow Data for ML Training</p>
                <p className="text-[10px] text-muted-foreground font-medium">
                  Permit your journal entries to be used for training our core language models
                </p>
              </div>
            </div>
            <Checkbox
              checked={settings.privacy.consent_ml_training}
              onChange={(e) => handleConsentChange('consent_ml_training', e.target.checked)}
              className="h-6 w-6 rounded-lg border-2 border-border/60"
            />
          </div>

          <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground">
                <Eye className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-bold">Allow Anonymous Research</p>
                <p className="text-[10px] text-muted-foreground font-medium">
                  Include your sanitized assessment scores in global platform dashboards
                </p>
              </div>
            </div>
            <Checkbox
              checked={settings.privacy.consent_aggregated_research}
              onChange={(e) => handleConsentChange('consent_aggregated_research', e.target.checked)}
              className="h-6 w-6 rounded-lg border-2 border-border/60"
            />
          </div>
        </div>
      </div>

      {/* Wellbeing Controls */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Shield className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Wellbeing Controls</h3>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div className="flex items-center justify-between p-5 bg-red-50/10 border border-red-200/40 rounded-2xl group hover:border-red-300/60 transition-all">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-red-50 border border-red-200/40 text-red-600">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-bold">Enable Crisis Support Interventions</p>
                <p className="text-[10px] text-muted-foreground font-medium">
                  Allow the system to detect and intervene during severe emotional distress.
                  This enables specialized sentiment analysis and UI alerts when needed.
                </p>
              </div>
            </div>
            <Checkbox
              checked={settings.privacy.crisis_mode_enabled}
              onChange={(e) => handleCrisisModeChange(e.target.checked)}
              className="h-6 w-6 rounded-lg border-2 border-red-300/60 data-[state=checked]:bg-red-600 data-[state=checked]:border-red-600"
            />
          </div>
        </div>
      </div>

      {/* Data Retention */}
      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-medium">Data Retention</h3>
          <p className="text-xs text-muted-foreground">How long to keep your data</p>
        </div>
        <Select
          value={settings.privacy.data_retention_days.toString()}
          onValueChange={(value: string) => handleRetentionChange(parseInt(value))}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30">30 days</SelectItem>
            <SelectItem value="90">90 days</SelectItem>
            <SelectItem value="365">1 year</SelectItem>
            <SelectItem value="730">2 years</SelectItem>
            <SelectItem value="1825">5 years</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Eye className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Public Exposure</h3>
        </div>
        <Select value={settings.privacy.profile_visibility} onValueChange={handleVisibilityChange}>
          <SelectTrigger className="w-full h-11 rounded-xl bg-muted/10 border-border/40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-xl border-border/40">
            <SelectItem value="private">Restricted (Private)</SelectItem>
            <SelectItem value="friends">Extended Network (Friends)</SelectItem>
            <SelectItem value="public">Global (Public)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Utilities */}
      <div className="space-y-6 pt-4">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Download className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Data Portability</h3>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl gap-4">
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-xl bg-background border border-border/40 text-muted-foreground">
              <Download className="h-4 w-4" />
            </div>
            <p className="text-xs font-bold">Request Comprehensive Data Export</p>
          </div>
          <Button
            variant="outline"
            onClick={handleExportData}
            disabled={isDownloading}
            className="w-full sm:w-auto font-black uppercase tracking-widest text-[10px] h-9 rounded-full px-8 border-border/60 hover:bg-primary/5 hover:text-primary transition-colors"
          >
            {isDownloading ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                Generating...
              </>
            ) : (
              'Initiate Transfer'
            )}
          </Button>
        </div>
      </div>

      {/* Irreversible Actions */}
      <div className="space-y-6 pt-10 border-t border-destructive/20">
        <div className="flex items-center gap-2 text-destructive/60">
          <AlertTriangle className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Critical Actions</h3>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between p-6 bg-destructive/5 border border-destructive/10 rounded-2xl gap-6">
          <div className="space-y-1 text-center sm:text-left">
            <p className="text-sm font-black text-destructive">Deactivate Personal Identity</p>
            <p className="text-[10px] text-destructive/60 font-medium">
              Permanently purge all assessment results, journals, and credentials.
            </p>
          </div>
          <Button
            variant="destructive"
            onClick={handleDeleteAccount}
            className="w-full sm:w-auto font-black uppercase tracking-widest text-[10px] h-10 rounded-full px-10 shadow-lg shadow-destructive/20"
          >
            Final Deletion
          </Button>
        </div>
      </div>
    </div>
  );
}
