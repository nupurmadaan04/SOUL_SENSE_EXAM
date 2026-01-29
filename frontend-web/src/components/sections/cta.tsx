'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Section } from '@/components/layout';
import { analytics } from '@/lib/utils/analytics';

export function CTA() {
  return (
    <Section className="relative overflow-hidden mb-20">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-br from-primary to-secondary p-12 lg:p-20 text-center text-white relative shadow-2xl"
      >
        {/* Background Sparkles */}
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <div className="absolute top-10 left-10 h-1 w-1 bg-white rounded-full animate-ping" />
          <div className="absolute bottom-10 right-10 h-1 w-1 bg-white rounded-full animate-ping" />
          <div className="absolute top-1/2 left-20 h-1 w-1 bg-white rounded-full animate-ping delay-700" />
        </div>

        <div className="relative z-10 space-y-8">
          <h2 className="text-4xl lg:text-5xl font-extrabold tracking-tight">
            Ready to Discover the Real You?
          </h2>
          <p className="text-lg lg:text-xl text-white/80 max-w-2xl mx-auto leading-relaxed">
            Join over 50,000 users who have already started their journey to higher emotional
            intelligence. Start your free test today.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <Button
              size="lg"
              variant="secondary"
              className="h-14 px-10 rounded-full text-lg font-bold group"
              asChild
              onClick={() =>
                analytics.trackEvent({
                  category: 'CTA',
                  action: 'click',
                  label: 'Bottom Start Free Test',
                })
              }
            >
              <Link href="/register">
                Start Free Test
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="h-14 px-10 rounded-full text-lg font-bold border-white/20 hover:bg-white/10 text-white"
              asChild
              onClick={() =>
                analytics.trackEvent({ category: 'CTA', action: 'click', label: 'Bottom Login' })
              }
            >
              <Link href="/login">Log in to Account</Link>
            </Button>
          </div>
        </div>
      </motion.div>
    </Section>
  );
}
