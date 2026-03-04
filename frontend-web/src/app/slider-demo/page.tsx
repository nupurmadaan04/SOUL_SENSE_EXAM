'use client';

import { Slider, EmotionIntensitySlider } from '@/components/ui';
import { useState } from 'react';

export default function SliderDemo() {
  const [moodRating, setMoodRating] = useState(5);
  const [energyLevel, setEnergyLevel] = useState(5);
  const [stressLevel, setStressLevel] = useState(5);
  const [volume, setVolume] = useState(50);
  const [brightness, setBrightness] = useState(75);
  const [fontSize, setFontSize] = useState(16);

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-12">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold mb-4 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Slider Components
          </h1>
          <p className="text-muted-foreground text-lg">
            Compare the basic slider with the new premium Emotion Intensity Slider.
          </p>
        </div>

        {/* Premium Emotion Intensity Sliders */}
        <section className="space-y-8">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold">Premium Emotion Sliders</h2>
            <span className="px-2 py-0.5 rounded text-[10px] bg-primary text-primary-foreground font-bold uppercase tracking-wider">
              NEW
            </span>
          </div>

          <div className="grid grid-cols-1 gap-12 p-8 rounded-[2rem] bg-secondary/10 border border-secondary/20 shadow-2xl">
            {/* Mood */}
            <EmotionIntensitySlider
              label="Mood Intensity"
              value={moodRating}
              onChange={setMoodRating}
              type="mood"
            />

            {/* Energy */}
            <EmotionIntensitySlider
              label="Energy Level"
              value={energyLevel}
              onChange={setEnergyLevel}
              type="energy"
            />

            {/* Stress */}
            <EmotionIntensitySlider
              label="Stress Level"
              value={stressLevel}
              onChange={setStressLevel}
              type="stress"
            />
          </div>
        </section>

        {/* Basic Slider Comparison */}
        <section className="space-y-6">
          <h2 className="text-2xl font-bold">Basic Sliders (Legacy)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="p-6 rounded-2xl bg-muted/50 border border-border">
              <Slider
                label="Basic Mood Rating"
                showValue
                min={1}
                max={10}
                step={1}
                value={moodRating}
                onChange={setMoodRating}
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-2 px-1 font-medium">
                <span>Sad</span>
                <span>Neutral</span>
                <span>Happy</span>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-muted/50 border border-border">
              <Slider
                label="System Volume"
                showValue
                min={0}
                max={100}
                step={5}
                value={volume}
                onChange={setVolume}
              />
            </div>
          </div>
        </section>

        {/* Features Table */}
        <section className="bg-card p-8 rounded-3xl border shadow-xl">
          <h2 className="text-2xl font-bold mb-6">Enhancements</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
                1
              </div>
              <div>
                <p className="font-bold">Animated UI</p>
                <p className="text-xs text-muted-foreground">Smooth transitions and spring physics</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
                2
              </div>
              <div>
                <p className="font-bold">Visual Feedback</p>
                <p className="text-xs text-muted-foreground">Dynamic emoji scaling and color shifts</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
                3
              </div>
              <div>
                <p className="font-bold">Immediate Response</p>
                <p className="text-xs text-muted-foreground">Zero latency with optimized state updates</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
                4
              </div>
              <div>
                <p className="font-bold">Premium Aesthetics</p>
                <p className="text-xs text-muted-foreground">Glowing tracks and magnetic thumbs</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
