'use client';

import React from 'react';
import { EmotionIntensitySlider } from '@/components/ui/emotion-intensity-slider';

interface MoodSliderProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
  showEmoji?: boolean;
}

/**
 * @deprecated Use EmotionIntensitySlider from @/components/ui instead.
 * This remains as a compatible wrapper for the journal folder.
 */
export function MoodSlider({ value, onChange, label, showEmoji = true }: MoodSliderProps) {
  return (
    <EmotionIntensitySlider
      value={value}
      onChange={onChange}
      label={label}
      showEmoji={showEmoji}
      type="mood"
    />
  );
}
