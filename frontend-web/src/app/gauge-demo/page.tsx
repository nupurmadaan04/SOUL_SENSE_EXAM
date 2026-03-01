'use client';

import React, { useState } from 'react';
import { ScoreGauge } from '@/lib/dynamic-imports';
import { Card, CardContent, CardHeader, CardTitle, Slider } from '@/components/ui';

export default function GaugeDemoPage() {
  const [score, setScore] = useState(75);

  return (
    <div className="container mx-auto py-10 space-y-10">
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">Score Gauge Showcase</h1>
        <p className="text-muted-foreground text-lg">
          A premium circular gauge for displaying EQ scores with fluid animations.
        </p>
      </div>

      <Card className="max-w-md mx-auto">
        <CardHeader>
          <CardTitle>Score Controller</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm font-medium">Current Score: {score}</span>
              <span className="text-sm text-muted-foreground">0 - 100</span>
            </div>
            <Slider value={score} max={100} step={1} onChange={setScore} />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-end">
        <Card>
          <CardHeader>
            <CardTitle className="text-center text-sm">Small Size (&apos;sm&apos;)</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center pb-8">
            <ScoreGauge score={score} size="sm" label="Mental Health Index" />
          </CardContent>
        </Card>

        <Card className="border-primary/20 shadow-lg shadow-primary/10">
          <CardHeader>
            <CardTitle className="text-center text-sm">Medium Size (&apos;md&apos;)</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center pb-8">
            <ScoreGauge score={score} size="md" label="Overall EQ Score" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-center text-sm">Large Size (&apos;lg&apos;)</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center pb-8">
            <ScoreGauge score={score} size="lg" label="Emotional Assessment" />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card flex flex-col items-center gap-2">
          <span className="text-xs font-bold text-red-500 uppercase">Needs Work (0-40)</span>
          <ScoreGauge score={25} size="sm" showLabel={false} animated={false} />
        </div>
        <div className="p-4 rounded-xl border bg-card flex flex-col items-center gap-2">
          <span className="text-xs font-bold text-amber-500 uppercase">Developing (41-60)</span>
          <ScoreGauge score={52} size="sm" showLabel={false} animated={false} />
        </div>
        <div className="p-4 rounded-xl border bg-card flex flex-col items-center gap-2">
          <span className="text-xs font-bold text-emerald-500 uppercase">Good (61-80)</span>
          <ScoreGauge score={78} size="sm" showLabel={false} animated={false} />
        </div>
        <div className="p-4 rounded-xl border bg-card flex flex-col items-center gap-2">
          <span className="text-xs font-bold text-indigo-600 uppercase">Excellent (81-100)</span>
          <ScoreGauge score={95} size="sm" showLabel={false} animated={false} />
        </div>
      </div>
    </div>
  );
}
