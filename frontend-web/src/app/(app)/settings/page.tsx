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
  Info,
  RefreshCw,
} from 'lucide-react';
import { usePreferences } from '@/hooks/usePreferences';
import { SystemPreferences } from '@/components/settings';

const tabs = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'preferences', label: 'System Preferences', icon: SettingsIcon },
  { id: 'privacy', label: 'Privacy & Data', icon: Shield },
  { id: 'ai-guidelines', label: 'AI Trust', icon: ShieldAlert },
  { id: 'account', label: 'Account', icon: UserIcon },
  { id: 'about', label: 'About', icon: Info },
];

export default function SettingsPage() {
  const { settings, isLoading, error, updateSettings, syncSettings } = useSettings();
  const {
    preferences,
    isLoading: isPrefsLoading,
    saveStatus: prefsSaveStatus,
    updatePreferencesDebounced,
  } = usePreferences();
  const [activeTab, setActiveTab] = useState('appearance');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [isMobile, setIsMobile] = useState(false);

  // Handle URL hash for direct tab links
  useEffect(() => {
    const hash = window.location.hash.replace('#', '');
    if (hash && tabs.some((tab) => tab.id === hash)) {
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

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-6 space-y-12">
        <Skeleton className="h-12 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <Skeleton className="lg:col-span-3 h-[400px] rounded-2xl" />
          <Skeleton className="lg:col-span-9 h-[600px] rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-6">
        <div className="text-center bg-destructive/5 p-12 rounded-3xl border border-destructive/10">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-6" />
          <p className="text-destructive font-black mb-6 text-xl">System Error: {error}</p>
          <Button
            onClick={() => window.location.reload()}
            variant="outline"
            className="font-bold rounded-full px-8"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="max-w-6xl mx-auto py-12 px-6 space-y-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-6 border-b border-border/40 pb-8">
        <div className="space-y-1">
          <h1 className="text-4xl font-black tracking-tight text-foreground flex items-center gap-4">
            Settings
          </h1>
          <p className="text-muted-foreground font-medium opacity-70">
            Configure your experience and manage your data.
          </p>
        </div>

        {/* Action Bar */}
        <div className="flex items-center gap-4 bg-muted/20 p-2 rounded-2xl border border-border/40">
          <div className="px-4">
            {(saveStatus === 'saving' || prefsSaveStatus === 'saving') && (
              <div className="flex items-center gap-2 text-primary">
                <div className="animate-spin h-3 w-3 border-2 border-primary border-t-transparent rounded-full" />
                <span className="text-[10px] font-black uppercase tracking-widest">Saving</span>
              </div>
            )}
            {(saveStatus === 'saved' || prefsSaveStatus === 'saved') &&
              saveStatus !== 'saving' &&
              prefsSaveStatus !== 'saving' && (
                <div className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle className="h-3 w-3" />
                  <span className="text-[10px] font-black uppercase tracking-widest">Saved</span>
                </div>
              )}
            {(saveStatus === 'error' || prefsSaveStatus === 'error') && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-3 w-3" />
                <span className="text-[10px] font-black uppercase tracking-widest">Failed</span>
              </div>
            )}
            {saveStatus === 'idle' && prefsSaveStatus === 'idle' && (
              <div className="flex items-center gap-2 text-muted-foreground/40">
                <CheckCircle className="h-3 w-3" />
                <span className="text-[10px] font-black uppercase tracking-widest">Stable</span>
              </div>
            )}
          </div>
          <div className="w-[1px] h-6 bg-border/40" />
          <Button
            onClick={handleSync}
            variant="ghost"
            size="sm"
            className="font-extrabold text-[10px] uppercase tracking-widest hover:bg-background rounded-xl"
          >
            <RefreshCw className="mr-2 h-3 w-3" />
            Sync Cloud
          </Button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          orientation={isMobile ? 'horizontal' : 'vertical'}
          className="lg:col-span-12 grid grid-cols-1 lg:grid-cols-12 gap-10"
        >
          {/* Sidebar Navigation */}
          <div className="lg:col-span-3">
            <TabsList
              className={cn(
                'flex lg:flex-col bg-transparent h-auto gap-1 p-0',
                isMobile ? 'overflow-x-auto no-scrollbar pb-2' : 'sticky top-24'
              )}
            >
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 transition-all',
                      'data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-lg data-[state=active]:shadow-primary/20',
                      'data-[state=inactive]:hover:bg-muted/30 data-[state=inactive]:text-muted-foreground',
                      isMobile ? 'flex-1 min-w-[120px] justify-center' : 'justify-start w-full'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="font-bold text-sm">{tab.label}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

          {/* Content Area */}
          <div className="lg:col-span-9 space-y-6">
            <TabsContent value="appearance" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/5 text-primary">
                      <Palette className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Appearance</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <AppearanceSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="notifications" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-orange-500/5 text-orange-600">
                      <Bell className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Notifications</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <NotificationSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="preferences" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/5 text-primary">
                      <SettingsIcon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">System Preferences</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  {isPrefsLoading ? (
                    <div className="space-y-4">
                      <Skeleton className="h-20 w-full rounded-2xl" />
                      <Skeleton className="h-20 w-full rounded-2xl" />
                    </div>
                  ) : preferences ? (
                    <SystemPreferences
                      preferences={preferences}
                      onChange={updatePreferencesDebounced}
                    />
                  ) : (
                    <div className="text-center py-8">
                      <AlertCircle className="h-10 w-10 text-destructive mx-auto mb-4" />
                      <p className="text-muted-foreground font-medium">Failed to load preferences.</p>
                      <Button onClick={() => window.location.reload()} variant="link" className="mt-2">
                        Try refreshing the page
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="privacy" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-emerald-500/5 text-emerald-600">
                      <Shield className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Privacy & Data</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <PrivacySettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="ai-guidelines" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-primary/5 text-primary">
                      <ShieldAlert className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Data Privacy & AI Guidelines</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <AIBoundarySettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="account" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-blue-500/5 text-blue-600">
                      <UserIcon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">Account</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <AccountSettings settings={settings} onChange={handleSettingChange} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="about" className="mt-0 focus-visible:outline-none">
              <Card className="rounded-3xl border border-border/40 bg-background/60 backdrop-blur-md shadow-sm">
                <CardHeader className="p-8 border-b border-border/40">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-muted text-muted-foreground">
                      <Info className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl font-black">About</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-8">
                  <AboutSettings />
                </CardContent>
              </Card>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
