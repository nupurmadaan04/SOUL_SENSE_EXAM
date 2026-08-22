'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  Lock,
  EyeOff,
  Download,
  Trash2,
  KeyRound,
  FileCheck,
  Clock,
  Mail,
  Linkedin,
  Github,
  CheckCircle2,
} from 'lucide-react';
import { Footer, Section } from '@/components/layout';
import { Button } from '@/components/ui';

export default function PrivacyPolicyPage() {
  const lastUpdated = 'August 22, 2026';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-300">
      <main className="flex-grow pt-28 pb-20">
        <Section className="container mx-auto px-6 max-w-4xl">
          {/* Header Banner */}
          <div className="space-y-4 mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs font-bold uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" />
              Privacy & Security Center
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 dark:text-white">
              Privacy Policy
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Last Revised: {lastUpdated}
              </span>
              <span>•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                GDPR & CCPA Compliant
              </span>
            </div>

            {/* Page Tags */}
            <div className="flex flex-wrap gap-2 pt-2">
              {[
                'PrivacyPolicy',
                'GDPR',
                'CCPA',
                'ZeroKnowledge',
                'AES256GCM',
                'DataSovereignty',
                'EncryptedJournal',
              ].map((tag) => (
                <span
                  key={tag}
                  className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-white/10 text-slate-600 dark:text-slate-300 shadow-sm"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>

          {/* Core Privacy Pillars Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
            <div className="p-6 rounded-2xl bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 shadow-sm space-y-2">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                Zero-Knowledge Encryption
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Reflections and journal entries are encrypted client-side using AES-256 GCM before
                persistence.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 shadow-sm space-y-2">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-3">
                <EyeOff className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                Zero Data Monetization
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                We will never sell, rent, or trade your personal emotional or psychometric data to advertisers.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 shadow-sm space-y-2">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-3">
                <Download className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                Full Data Sovereignty
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Export your full telemetry anytime in JSON, CSV, or PDF, or delete your account in one click.
              </p>
            </div>
          </div>

          {/* Privacy Policy Detailed Document */}
          <div className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-3xl p-8 md:p-12 shadow-sm space-y-10 text-slate-700 dark:text-slate-300 leading-relaxed font-normal text-sm md:text-base">
            {/* Section 1 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">1.</span> Privacy Philosophy & Overview
              </h2>
              <p>
                At Soul Sense, we believe that emotional growth requires profound psychological safety.
                Our architecture adheres to <strong>Privacy by Design</strong> principles. We minimize
                data collection to only what is strictly necessary to calculate your psychometric
                scores and provide personalized reflective insights.
              </p>
            </section>

            {/* Section 2 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">2.</span> Information We Collect
              </h2>
              <ul className="list-disc pl-6 space-y-2 text-slate-600 dark:text-slate-300">
                <li>
                  <strong>Account Credentials:</strong> Username, email address, and Argon2id-hashed
                  passwords.
                </li>
                <li>
                  <strong>Psychometric Assessment Responses:</strong> Likert scale answers, dimension
                  timings, and computed score distributions.
                </li>
                <li>
                  <strong>Journal & Reflection Content:</strong> Encrypted text bodies, user-selected
                  mood scores, and reflection tags.
                </li>
                <li>
                  <strong>Security & Session Telemetry:</strong> Anonymized device fingerprints, IP
                  hashes for rate limiting, and JWT token rotation metadata.
                </li>
              </ul>
            </section>

            {/* Section 3 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">3.</span> Encryption & Security Standards
              </h2>
              <p>
                Soul Sense employs state-of-the-art cryptographic safeguards:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/5 space-y-1">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-900 dark:text-white">
                    In Transit
                  </span>
                  <p className="text-xs text-slate-500">
                    Enforced TLS 1.3 encryption with strict HTTP Strict Transport Security (HSTS).
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/5 space-y-1">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-900 dark:text-white">
                    At Rest
                  </span>
                  <p className="text-xs text-slate-500">
                    AES-256 GCM encryption for private journal fields and sensitive profile data.
                  </p>
                </div>
              </div>
            </section>

            {/* Section 4 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">4.</span> Your Rights under GDPR & CCPA
              </h2>
              <p>
                Regardless of your geographic location, Soul Sense extends universal privacy rights to
                all users:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-slate-600 dark:text-slate-300">
                <li>
                  <strong>Right to Access & Portability:</strong> Instantly export all your assessments,
                  scores, and journal entries via our `/api/v1/export` endpoints.
                </li>
                <li>
                  <strong>Right to Rectification:</strong> Edit or update any personal profile details
                  or journal reflections directly in your account dashboard.
                </li>
                <li>
                  <strong>Right to Erasure (Forget Me):</strong> Permanently delete your user record,
                  sessions, and all associated scores with complete cryptographic purge.
                </li>
              </ul>
            </section>

            {/* Section 5 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">5.</span> Cookies & Local Storage Usage
              </h2>
              <p>
                We use strictly necessary cookies (`refresh_token` with `httpOnly`, `Secure`, `SameSite=Lax`)
                and browser local storage to maintain authenticated sessions, store your dark/light
                theme preference, and cache assessment drafts offline. We do not use third-party
                tracking cookies.
              </p>
            </section>

            {/* Section 6 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-emerald-600 dark:text-emerald-400">6.</span> Data Protection Officer & Inquiries
              </h2>
              <p>
                For any privacy requests, data export inquiries, or security disclosures, please contact
                our lead maintainer:
              </p>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 space-y-1 text-sm">
                <p className="font-bold text-slate-900 dark:text-white">Nupur Madaan (Creator & Data Steward)</p>
                <p>
                  Email:{' '}
                  <a href="mailto:nupur.04.m@gmail.com" className="text-emerald-600 dark:text-emerald-400 underline">
                    nupur.04.m@gmail.com
                  </a>
                </p>
                <p>
                  LinkedIn:{' '}
                  <a
                    href="https://www.linkedin.com/in/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-600 dark:text-emerald-400 underline"
                  >
                    linkedin.com/in/nupurmadaan04
                  </a>
                </p>
              </div>
            </section>
          </div>
        </Section>
      </main>

      <Footer />
    </div>
  );
}
