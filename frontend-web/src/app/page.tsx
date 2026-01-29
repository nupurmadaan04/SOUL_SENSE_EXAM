'use client';

import { Navbar, Footer } from '@/components/layout';
import { Hero, Features, Testimonials, Newsletter, CTA } from '@/components/sections';
import { useEffect } from 'react';
import { analytics } from '@/lib/utils/analytics';

export default function Home() {
  useEffect(() => {
    analytics.trackPageView('/');
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-grow">
        <Hero />
        <Features />
        <Testimonials />
        <Newsletter />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
