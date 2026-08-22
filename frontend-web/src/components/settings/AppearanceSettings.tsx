'use client';

import { useState, useEffect } from 'react';
import { UserSettings } from '../../lib/api/settings';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui';
import { ThemeToggle, ThemeValue } from './theme-toggle';
import { Type, Eye } from 'lucide-react';
import { useTheme } from 'next-themes';
import { toast } from '@/lib/toast';

interface AppearanceSettingsProps {
  settings: UserSettings;
  onChange: (updates: Partial<UserSettings>) => void;
}

export function AppearanceSettings({ settings, onChange }: AppearanceSettingsProps) {
  const { setTheme } = useTheme();
  const [currentTheme, setCurrentTheme] = useState<ThemeValue>(
    (settings?.theme as ThemeValue) || 'system'
  );

  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('soulsense_font_size') as 'small' | 'medium' | 'large';
      if (saved) return saved;
    }
    return (settings?.accessibility?.font_size as 'small' | 'medium' | 'large') || 'medium';
  });

  const [highContrast, setHighContrast] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('soulsense_high_contrast') === 'true';
    }
    return settings?.accessibility?.high_contrast ?? false;
  });

  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('soulsense_reduced_motion') === 'true';
    }
    return settings?.accessibility?.reduced_motion ?? false;
  });

  useEffect(() => {
    if (settings?.theme) {
      setCurrentTheme(settings.theme as ThemeValue);
    }
    if (settings?.accessibility?.font_size) {
      setFontSize(settings.accessibility.font_size);
    }
    if (settings?.accessibility?.high_contrast !== undefined) {
      setHighContrast(settings.accessibility.high_contrast);
    }
    if (settings?.accessibility?.reduced_motion !== undefined) {
      setReducedMotion(settings.accessibility.reduced_motion);
    }
  }, [settings]);

  const handleThemeChange = (theme: ThemeValue) => {
    setCurrentTheme(theme);
    setTheme(theme);
    onChange({ theme });
  };

  const handleFontSizeChange = (newSize: 'small' | 'medium' | 'large') => {
    setFontSize(newSize);
    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('font-size-small', 'font-size-medium', 'font-size-large');
      document.documentElement.classList.add(`font-size-${newSize}`);
      try {
        localStorage.setItem('soulsense_font_size', newSize);
      } catch (e) {}
    }
    onChange({
      accessibility: {
        ...settings?.accessibility,
        font_size: newSize,
      },
    });
    toast.success(`Typography scale set to ${newSize}`);
  };

  const handleHighContrastToggle = (checked: boolean) => {
    setHighContrast(checked);
    if (typeof document !== 'undefined') {
      if (checked) {
        document.documentElement.classList.add('high-contrast');
      } else {
        document.documentElement.classList.remove('high-contrast');
      }
      try {
        localStorage.setItem('soulsense_high_contrast', String(checked));
      } catch (e) {}
    }
    onChange({
      accessibility: {
        ...settings?.accessibility,
        high_contrast: checked,
      },
    });
    toast.success(checked ? 'High Contrast mode enabled' : 'High Contrast mode disabled');
  };

  const handleReducedMotionToggle = (checked: boolean) => {
    setReducedMotion(checked);
    if (typeof document !== 'undefined') {
      if (checked) {
        document.documentElement.classList.add('reduced-motion');
      } else {
        document.documentElement.classList.remove('reduced-motion');
      }
      try {
        localStorage.setItem('soulsense_reduced_motion', String(checked));
      } catch (e) {}
    }
    onChange({
      accessibility: {
        ...settings?.accessibility,
        reduced_motion: checked,
      },
    });
    toast.success(checked ? 'Reduced Motion enabled' : 'Reduced Motion disabled');
  };

  return (
    <div className="space-y-10">
      {/* Theme Selection */}
      <ThemeToggle
        value={currentTheme}
        onChange={handleThemeChange}
      />

      {/* Font Size */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Type className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Content Typography</h3>
        </div>
        <Select value={fontSize} onValueChange={(val: any) => handleFontSizeChange(val)}>
          <SelectTrigger className="w-full h-12 rounded-xl bg-card border-border/80 text-foreground font-semibold">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-xl border-border/80 bg-popover text-popover-foreground">
            <SelectItem value="small">Comfortable (Small - 14px)</SelectItem>
            <SelectItem value="medium">Standard (Medium - 16px)</SelectItem>
            <SelectItem value="large">Spacious (Large - 18.5px)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Accessibility Flags */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Eye className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Visual Accessibility</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="flex items-center justify-between p-4 rounded-2xl bg-card border border-border/80 hover:border-primary/40 cursor-pointer transition-all shadow-sm">
            <div className="space-y-0.5">
              <p className="text-sm font-bold text-foreground">High Contrast</p>
              <p className="text-xs text-muted-foreground">Prioritize legibility over aesthetics</p>
            </div>
            <input
              type="checkbox"
              checked={highContrast}
              onChange={(e) => handleHighContrastToggle(e.target.checked)}
              className="h-5 w-5 rounded-md border-border text-primary focus:ring-primary/40 cursor-pointer accent-primary"
            />
          </label>

          <label className="flex items-center justify-between p-4 rounded-2xl bg-card border border-border/80 hover:border-primary/40 cursor-pointer transition-all shadow-sm">
            <div className="space-y-0.5">
              <p className="text-sm font-bold text-foreground">Reduced Motion</p>
              <p className="text-xs text-muted-foreground">Minimize animations and transitions</p>
            </div>
            <input
              type="checkbox"
              checked={reducedMotion}
              onChange={(e) => handleReducedMotionToggle(e.target.checked)}
              className="h-5 w-5 rounded-md border-border text-primary focus:ring-primary/40 cursor-pointer accent-primary"
            />
          </label>
        </div>
      </div>
    </div>
  );
}
