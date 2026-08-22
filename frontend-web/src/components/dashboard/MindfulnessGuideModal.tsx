'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Wind, Play, Pause, RotateCcw, ArrowRight, ShieldCheck, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

interface MindfulnessGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MindfulnessGuideModal({ isOpen, onClose }: MindfulnessGuideModalProps) {
  const [activeTab, setActiveTab] = useState<'breathing' | 'grounding'>('breathing');
  const [isBreathingActive, setIsBreathingActive] = useState(false);
  const [breathPhase, setBreathPhase] = useState<'Inhale' | 'Hold' | 'Exhale'>('Inhale');
  const [counter, setCounter] = useState(4);

  useEffect(() => {
    let timer: any;
    if (isBreathingActive) {
      timer = setInterval(() => {
        setCounter((prev) => {
          if (prev <= 1) {
            if (breathPhase === 'Inhale') {
              setBreathPhase('Hold');
              return 7;
            } else if (breathPhase === 'Hold') {
              setBreathPhase('Exhale');
              return 8;
            } else {
              setBreathPhase('Inhale');
              return 4;
            }
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      setBreathPhase('Inhale');
      setCounter(4);
    }
    return () => clearInterval(timer);
  }, [isBreathingActive, breathPhase]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-border/80 bg-card/95 p-6 sm:p-8 shadow-2xl backdrop-blur-xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-border/40">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-yellow-500/15 text-yellow-600 dark:text-yellow-400">
                <Wind className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">Mindfulness & Breathing Guide</h3>
                <p className="text-xs text-muted-foreground">Calm your nervous system & center your mind</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex gap-2 my-4 p-1 bg-muted/40 rounded-2xl border border-border/40">
            <button
              onClick={() => setActiveTab('breathing')}
              className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'breathing'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              4-7-8 Breathing Technique
            </button>
            <button
              onClick={() => setActiveTab('grounding')}
              className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'grounding'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              5-4-3-2-1 Grounding Rule
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'breathing' ? (
            <div className="flex flex-col items-center justify-center py-4 space-y-6">
              <div className="relative flex items-center justify-center w-48 h-48">
                {/* Animated Pulsing Ring */}
                <motion.div
                  animate={
                    isBreathingActive
                      ? {
                          scale: breathPhase === 'Inhale' ? 1.3 : breathPhase === 'Hold' ? 1.3 : 1.0,
                          opacity: breathPhase === 'Inhale' ? 0.8 : breathPhase === 'Hold' ? 0.9 : 0.4,
                        }
                      : { scale: 1, opacity: 0.3 }
                  }
                  transition={{ duration: breathPhase === 'Inhale' ? 4 : breathPhase === 'Hold' ? 0 : 8, ease: 'easeInOut' }}
                  className="absolute inset-0 rounded-full bg-gradient-to-tr from-primary/30 to-secondary/30 blur-md"
                />

                <div className="relative z-10 flex flex-col items-center justify-center w-36 h-36 rounded-full border-2 border-primary/40 bg-card/90 shadow-inner">
                  <span className="text-xs font-bold uppercase tracking-widest text-primary">
                    {isBreathingActive ? breathPhase : 'Ready'}
                  </span>
                  <span className="text-3xl font-black text-foreground my-1">
                    {isBreathingActive ? counter : '4-7-8'}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {isBreathingActive
                      ? breathPhase === 'Inhale'
                        ? 'Breathe in slowly'
                        : breathPhase === 'Hold'
                        ? 'Hold gently'
                        : 'Slow exhale'
                      : 'Press Start'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  onClick={() => setIsBreathingActive(!isBreathingActive)}
                  className="gap-2 rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 px-6 font-bold shadow-md"
                >
                  {isBreathingActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {isBreathingActive ? 'Pause' : 'Start Breathing Exercise'}
                </Button>
                {isBreathingActive && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsBreathingActive(false);
                      setBreathPhase('Inhale');
                      setCounter(4);
                    }}
                    className="rounded-2xl gap-1.5"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Reset
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-3 py-2 text-xs">
              <div className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1">
                <p className="font-bold text-foreground">👀 5 Things you can SEE</p>
                <p className="text-muted-foreground text-[11px]">Notice small details around you: colors, shapes, light.</p>
              </div>
              <div className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1">
                <p className="font-bold text-foreground">✋ 4 Things you can TOUCH</p>
                <p className="text-muted-foreground text-[11px]">Feel your clothes, chair, desk, or hands together.</p>
              </div>
              <div className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1">
                <p className="font-bold text-foreground">👂 3 Things you can HEAR</p>
                <p className="text-muted-foreground text-[11px]">Listen for ambient sounds, wind, or distant murmurs.</p>
              </div>
              <div className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1">
                <p className="font-bold text-foreground">👃 2 Things you can SMELL</p>
                <p className="text-muted-foreground text-[11px]">Notice scents in the air or your own breath.</p>
              </div>
              <div className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1">
                <p className="font-bold text-foreground">👅 1 Thing you can TASTE</p>
                <p className="text-muted-foreground text-[11px]">Sip some water or notice the clean taste in your mouth.</p>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-4 mt-2 border-t border-border/40">
            <Link
              href="/journal"
              onClick={onClose}
              className="text-xs font-bold text-primary hover:underline inline-flex items-center gap-1"
            >
              Want to log this in Journal? <ArrowRight className="h-3 w-3" />
            </Link>
            <Button variant="ghost" onClick={onClose} className="rounded-xl text-xs font-semibold">
              Done
            </Button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
