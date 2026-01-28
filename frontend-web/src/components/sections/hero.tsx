'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui';
import Link from 'next/link';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Section } from '@/components/layout';
import { analytics } from '@/lib/utils/analytics';

export function Hero() {
  return (
    <Section className="pt-32 lg:pt-48 overflow-hidden relative">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/20 blur-[120px] rounded-full" />
      </div>

      <div className="flex flex-col items-center text-center gap-8 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border bg-background/50 backdrop-blur-sm text-sm font-medium text-primary shadow-sm"
        >
          <Sparkles className="h-4 w-4" />
          <span>Unlock Your Emotional Potential</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]"
        >
          Decode Your Emotions with{' '}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-primary bg-[length:200%_auto] animate-gradient">
            Soul Sense
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-xl text-muted-foreground leading-relaxed max-w-2xl"
        >
          Step into a world of self-awareness. Our AI-powered emotional intelligence test provides
          deep insights into your feelings, helping you build better relationships and a stronger
          mind.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
        >
          <Button
            size="lg"
            className="h-14 px-8 rounded-full text-lg group bg-gradient-to-r from-primary to-secondary"
            asChild
            onClick={() =>
              analytics.trackEvent({
                category: 'CTA',
                action: 'click',
                label: 'Hero Start Free Test',
              })
            }
          >
            <Link href="/register">
              Start Free EQ Test
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="h-14 px-8 rounded-full text-lg"
            asChild
            onClick={() =>
              analytics.trackEvent({ category: 'CTA', action: 'click', label: 'Hero Learn More' })
            }
          >
            <Link href="#features">Learn How It Works</Link>
          </Button>
        </motion.div>

        {/* Hero Visual Placeholder */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="mt-16 relative w-full aspect-[16/9] max-w-5xl rounded-2xl border bg-accent/50 backdrop-blur-md overflow-hidden shadow-2xl group"
        >
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-transparent to-secondary/10" />
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Mock Dashboard Visual */}
            <div className="w-[80%] h-[70%] bg-background/40 rounded-xl border border-dashed border-muted-foreground/30 flex flex-col p-6 gap-6">
              <div className="flex gap-4">
                <div className="h-3 w-16 bg-primary/20 rounded-full" />
                <div className="h-3 w-32 bg-secondary/20 rounded-full" />
              </div>
              <div className="grid grid-cols-3 gap-4 h-full">
                <div className="bg-primary/5 rounded-lg border border-primary/10" />
                <div className="bg-secondary/5 rounded-lg border border-secondary/10" />
                <div className="bg-primary/5 rounded-lg border border-primary/10" />
              </div>
            </div>
          </div>
          <div className="absolute bottom-6 left-6 flex items-center gap-2 bg-background/80 px-3 py-1.5 rounded-lg border text-xs font-medium backdrop-blur-sm">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span>Real-time EQ Analysis Active</span>
          </div>
        </motion.div>
      </div>
    </Section>
  );
}
