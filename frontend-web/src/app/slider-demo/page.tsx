'use client';

import { Slider } from '@/components/ui';
import { useState } from 'react';

export default function SliderDemo() {
  const [moodRating, setMoodRating] = useState(5);
  const [volume, setVolume] = useState(50);
  const [brightness, setBrightness] = useState(75);
  const [fontSize, setFontSize] = useState(16);

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-2">Slider Component Demo</h1>
          <p className="text-muted-foreground">Range slider for mood ratings, settings, and numeric inputs.</p>
        </div>

        {/* Mood Rating Example */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Mood Rating</h2>
          <div className="max-w-md">
            <Slider
              label="How are you feeling today?"
              showValue
              min={1}
              max={10}
              step={1}
              value={moodRating}
              onChange={setMoodRating}
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>Very Sad</span>
              <span>Neutral</span>
              <span>Very Happy</span>
            </div>
          </div>
        </div>

        {/* Settings Examples */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold">Settings Examples</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Volume Control */}
            <div className="space-y-2">
              <Slider
                label="Volume"
                showValue
                min={0}
                max={100}
                step={5}
                value={volume}
                onChange={setVolume}
              />
            </div>

            {/* Brightness Control */}
            <div className="space-y-2">
              <Slider
                label="Screen Brightness"
                showValue
                min={0}
                max={100}
                step={10}
                value={brightness}
                onChange={setBrightness}
              />
            </div>

            {/* Font Size Control */}
            <div className="space-y-2">
              <Slider
                label="Font Size"
                showValue
                min={12}
                max={24}
                step={1}
                value={fontSize}
                onChange={setFontSize}
              />
            </div>

            {/* Custom Range */}
            <div className="space-y-2">
              <Slider
                label="Custom Range (0.0 - 5.0)"
                showValue
                min={0}
                max={5}
                step={0.1}
                value={2.5}
                onChange={() => {}}
              />
            </div>
          </div>
        </div>

        {/* Different Sizes and Styles */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Different Configurations</h2>
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Without Label</p>
              <div className="max-w-md">
                <Slider
                  showValue
                  min={0}
                  max={100}
                  value={65}
                  onChange={() => {}}
                />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">Without Value Display</p>
              <div className="max-w-md">
                <Slider
                  label="Quiet Setting"
                  min={0}
                  max={10}
                  step={1}
                  value={3}
                  onChange={() => {}}
                />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">Large Step Values</p>
              <div className="max-w-md">
                <Slider
                  label="Temperature (°C)"
                  showValue
                  min={-10}
                  max={40}
                  step={5}
                  value={20}
                  onChange={() => {}}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Accessibility Features */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Accessibility Features</h2>
          <div className="bg-muted p-4 rounded-lg">
            <ul className="text-sm space-y-2">
              <li>✅ <strong>Keyboard Navigation:</strong> Use arrow keys to adjust values</li>
              <li>✅ <strong>Screen Reader Support:</strong> Proper ARIA labels and semantic HTML</li>
              <li>✅ <strong>Touch Support:</strong> Works on mobile devices with touch gestures</li>
              <li>✅ <strong>Focus Management:</strong> Visible focus indicators for keyboard users</li>
              <li>✅ <strong>High Contrast:</strong> Styled with design system colors</li>
            </ul>
          </div>
        </div>

        {/* Usage Examples */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Usage Examples</h2>
          <div className="bg-muted p-4 rounded-lg">
            <pre className="text-sm overflow-x-auto">
{`// Basic slider
<Slider
  value={rating}
  onChange={setRating}
  min={1}
  max={10}
/>

// With label and value display
<Slider
  label="Mood Rating"
  showValue
  value={mood}
  onChange={setMood}
  min={1}
  max={10}
  step={1}
/>

// Settings slider
<Slider
  label="Volume"
  showValue
  value={volume}
  onChange={setVolume}
  min={0}
  max={100}
  step={5}
/>`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}