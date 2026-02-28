'use client';

import { UserPreferences } from '@/lib/api/preferences';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Switch,
} from '@/components/ui';
import { Mail, Calendar, Moon, BellRing, Clock } from 'lucide-react';

interface SystemPreferencesProps {
    preferences: UserPreferences;
    onChange: (updates: Partial<UserPreferences>) => void;
}

export function SystemPreferences({ preferences, onChange }: SystemPreferencesProps) {
    return (
        <div className="space-y-12">
            {/* Notification Preferences */}
            <div className="space-y-6">
                <div className="flex items-center gap-2 text-muted-foreground/60">
                    <BellRing className="h-3.5 w-3.5" />
                    <h3 className="text-[10px] uppercase tracking-widest font-black">Notification Channels</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
                        <div className="flex items-center gap-4">
                            <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                                <Mail className="h-5 w-5" />
                            </div>
                            <div className="space-y-0.5">
                                <p className="text-sm font-bold">Email Notifications</p>
                                <p className="text-[10px] text-muted-foreground font-medium">
                                    Receive alerts and updates via email
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={preferences.email_notifications}
                            onCheckedChange={(checked) => onChange({ email_notifications: checked })}
                        />
                    </div>

                    <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
                        <div className="flex items-center gap-4">
                            <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                                <Calendar className="h-5 w-5" />
                            </div>
                            <div className="space-y-0.5">
                                <p className="text-sm font-bold">Weekly Digest</p>
                                <p className="text-[10px] text-muted-foreground font-medium">
                                    Summary of your weekly psychological growth
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={preferences.weekly_digest}
                            onCheckedChange={(checked) => onChange({ weekly_digest: checked })}
                        />
                    </div>
                </div>
            </div>

            {/* Assessment Frequency */}
            <div className="space-y-6">
                <div className="flex items-center gap-2 text-muted-foreground/60">
                    <Clock className="h-3.5 w-3.5" />
                    <h3 className="text-[10px] uppercase tracking-widest font-black">Assessment Spacing</h3>
                </div>

                <div className="p-6 bg-muted/10 border border-border/40 rounded-2xl space-y-4">
                    <div className="space-y-1">
                        <p className="text-sm font-bold">Frequency Interval</p>
                        <p className="text-xs text-muted-foreground font-medium">
                            How often you would like to receive comprehensive assessments.
                        </p>
                    </div>
                    <Select
                        value={preferences.assessment_frequency_days.toString()}
                        onValueChange={(value) =>
                            onChange({ assessment_frequency_days: parseInt(value) as 7 | 14 | 30 })
                        }
                    >
                        <SelectTrigger className="w-full h-12 rounded-xl bg-background border-border/40">
                            <SelectValue placeholder="Select frequency" />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl border-border/40">
                            <SelectItem value="7">Every 7 Days (Frequent)</SelectItem>
                            <SelectItem value="14">Every 14 Days (Standard)</SelectItem>
                            <SelectItem value="30">Every 30 Days (Monthly)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* Interface Preferences */}
            <div className="space-y-6">
                <div className="flex items-center gap-2 text-muted-foreground/60">
                    <Moon className="h-3.5 w-3.5" />
                    <h3 className="text-[10px] uppercase tracking-widest font-black">Visual Experience</h3>
                </div>

                <div className="flex items-center justify-between p-5 bg-muted/10 border border-border/40 rounded-2xl group hover:border-border transition-all">
                    <div className="flex items-center gap-4">
                        <div className="p-2 rounded-xl bg-background border border-border/40 text-muted-foreground group-hover:text-primary transition-colors">
                            <Moon className="h-5 w-5" />
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-sm font-bold">Dark Mode Sync</p>
                            <p className="text-[10px] text-muted-foreground font-medium">
                                Persist your theme preference to the cloud database
                            </p>
                        </div>
                    </div>
                    <Switch
                        checked={preferences.dark_mode_preference}
                        onCheckedChange={(checked) => onChange({ dark_mode_preference: checked })}
                    />
                </div>
            </div>
        </div>
    );
}
