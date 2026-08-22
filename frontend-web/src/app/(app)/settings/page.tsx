'use client';

import { useState, useEffect } from 'react';
import { useSettings } from '@/hooks/useSettings';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Button } from '@/components/ui';
import { Skeleton } from '@/components/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui';
import {
  AppearanceSettings,
  NotificationSettings,
  PrivacySettings,
  AccountSettings,
  AboutSettings,
  AIBoundarySettings,
} from '@/components/settings';
import { cn } from '@/lib/utils';
import {
  CheckCircle,
  AlertCircle,
  Settings as SettingsIcon,
  Palette,
  Bell,
  Shield,
  ShieldAlert,
  User as UserIcon,
  HelpCircle,
  Info,
  RefreshCw,
} from 'lucide-react';
import { usePreferences } from '@/hooks/usePreferences';
import { SystemPreferences } from '@/components/settings';
import { useOnboarding } from '@/hooks/useOnboarding';

const tabs = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'preferences', label: 'System Preferences', icon: SettingsIcon },
  { id: 'privacy', label: 'Privacy & Data', icon: Shield },
  { id: 'ai-guidelines', label: 'AI Trust', icon: ShieldAlert },
  { id: 'account', label: 'Account', icon: UserIcon },
  { id: 'support', label: 'Help & Support', icon: HelpCircle },
];

export default function SettingsPage() {
  const { settings, isLoading, error, updateSettings, syncSettings } = useSettings();
  const {
    preferences,
    isLoading: isPrefsLoading,
    saveStatus: prefsSaveStatus,
    updatePreferencesDebounced,
  } = usePreferences();
  const { restartTutorial } = useOnboarding();
  const [activeTab, setActiveTab] = useState('appearance');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [isMobile, setIsMobile] = useState(false);

  // Handle URL hash for direct tab links
  useEffect(() => {
    const hash = window.location.hash.replace('#', '');
    if (hash === 'support' || hash === 'about') {
      setActiveTab('support');
    } else if (hash && tabs.some((tab) => tab.id === hash)) {
      setActiveTab(hash);
    }
  }, []);

  // Update URL hash when tab changes
  useEffect(() => {
    window.location.hash = activeTab;
  }, [activeTab]);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleSettingChange = async (updates: any) => {
    setSaveStatus('saving');
    try {
      await updateSettings(updates);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const handleSync = async () => {
    try {
      await syncSettings();
    } catch (err) {
      console.error('Failed to sync settings:', err);
    }
  };

  return (
    <div className="p-4 md:p-10 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/40 pb-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
            Settings &amp; Support
          </h1>
          <p className="text-muted-foreground mt-1 text-sm font-medium">
            Manage your personal preferences, privacy settings, and view support guides
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveStatus === 'saving' && (
            <span className="text-xs font-bold text-muted-foreground animate-pulse flex items-center gap-1.5 bg-muted/40 px-3 py-1.5 rounded-full border border-border/40">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Saving...
            </span>
          )}
          {saveStatus === 'saved' && (
            <span className="text-xs font-bold text-emerald-500 flex items-center gap-1.5 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
              <CheckCircle className="h-3.5 w-3.5" /> Saved
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="text-xs font-bold text-destructive flex items-center gap-1.5 bg-destructive/10 px-3 py-1.5 rounded-full border border-destructive/20">
              <AlertCircle className="h-3.5 w-3.5" /> Error Saving
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            className="rounded-full gap-2 border-border/60 hover:bg-muted/40"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Sync Cloud</span>
          </Button>
        </div>
      </div>

      {/* Main Settings Tabs */}
      <div className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          {/* Tabs Navigation */}
          <div className="overflow-x-auto pb-2 scrollbar-none">
            <TabsList className="h-auto p-1.5 bg-muted/30 border border-border/40 rounded-2xl flex flex-nowrap sm:flex-wrap gap-1.5 min-w-max sm:min-w-0">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className={cn(
                      'flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all duration-200 cursor-pointer shrink-0',
                      isActive
                        ? 'bg-background text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground hover:bg-background/40'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.label}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

          {/* Tabs Content Sections */}
          <div className="mt-6">
            <TabsContent value="appearance" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/10 text-primary">
                      <Palette className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Appearance</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <AppearanceSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="notifications" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500">
                      <Bell className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Notifications</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <NotificationSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="preferences" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/10 text-primary">
                      <SettingsIcon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">System Preferences</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <SystemPreferences
                    preferences={preferences}
                    isLoading={isPrefsLoading}
                    saveStatus={prefsSaveStatus}
                    onUpdatePreferences={updatePreferencesDebounced}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="privacy" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
                      <Shield className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Privacy &amp; Data Security</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <PrivacySettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="ai-guidelines" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500">
                      <ShieldAlert className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">AI Boundaries &amp; Trust</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <AIBoundarySettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="account" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500">
                      <UserIcon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Account</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <AccountSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="support" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-card/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-6 sm:p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/10 text-primary">
                      <HelpCircle className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Help, FAQs &amp; Support</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-6 sm:p-8">
                  <AboutSettings onRestartTutorial={restartTutorial} />
                </CardContent>
              </Card>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
