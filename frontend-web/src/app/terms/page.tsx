'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  FileText,
  Shield,
  AlertTriangle,
  Lock,
  UserCheck,
  Scale,
  Clock,
  ArrowRight,
  Mail,
} from 'lucide-react';
import { Footer, Section } from '@/components/layout';
import { Button } from '@/components/ui';

export default function TermsOfServicePage() {
  const lastUpdated = 'August 22, 2026';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-300">
      <main className="flex-grow pt-28 pb-20">
        <Section className="container mx-auto px-6 max-w-4xl">
          {/* Header Banner */}
          <div className="space-y-4 mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-bold uppercase tracking-wider">
              <Scale className="w-3.5 h-3.5" />
              Legal & Compliance
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 dark:text-white">
              Terms of Service
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Last Revised: {lastUpdated}
              </span>
              <span>•</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                Version 2.4.0 (Production)
              </span>
            </div>

            {/* Page Tags */}
            <div className="flex flex-wrap gap-2 pt-2">
              {[
                'TermsOfService',
                'UserAgreement',
                'PsychometricDisclaimer',
                'ZeroKnowledgePrivacy',
                'DataOwnership',
                'OpenSource',
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

          {/* Important Notice Banner */}
          <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 mb-10 flex items-start gap-4">
            <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1 text-sm leading-relaxed">
              <h3 className="font-bold text-amber-900 dark:text-amber-100">
                Psychometric & Medical Disclaimer
              </h3>
              <p>
                Soul Sense is an educational, self-reflection, and personal development platform.
                Our psychometric scores, neural waveforms, and sentiment analyses are designed for
                metacognitive training and personal growth. Soul Sense is <strong>not a medical, psychiatric, or clinical diagnostic service</strong>.
              </p>
            </div>
          </div>

          {/* Terms Content Sections */}
          <div className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-3xl p-8 md:p-12 shadow-sm space-y-10 text-slate-700 dark:text-slate-300 leading-relaxed font-normal text-sm md:text-base">
            {/* Section 1 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">1.</span> Acceptance of Terms & Eligibility
              </h2>
              <p>
                By accessing, registering for, or using Soul Sense (including the web application,
                mobile interfaces, API endpoints, and associated services), you acknowledge that you
                have read, understood, and agreed to be legally bound by these Terms of Service and
                our Privacy Policy.
              </p>
              <p>
                You must be at least 13 years of age (or the minimum legal age required in your
                jurisdiction) to create an account. If you are using Soul Sense on behalf of an
                organization or research institution, you represent and warrant that you have full
                authority to bind that entity to these Terms.
              </p>
            </section>

            {/* Section 2 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">2.</span> Account Registration, Security & Sessions
              </h2>
              <p>
                When you create an account, you agree to provide accurate, current, and complete
                information. You are solely responsible for maintaining the confidentiality of your
                account credentials, password, multi-factor authentication (MFA/2FA) tokens, and for
                any activities occurring under your account.
              </p>
              <p>
                Soul Sense utilizes device fingerprinting, session concurrency detection, and token
                revocation guards to prevent unauthorized access. If you suspect any unauthorized
                activity or compromised credentials, notify our security team immediately at{' '}
                <a
                  href="mailto:nupur.04.m@gmail.com"
                  className="text-indigo-600 dark:text-indigo-400 underline font-medium"
                >
                  nupur.04.m@gmail.com
                </a>.
              </p>
            </section>

            {/* Section 3 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">3.</span> Intellectual Property & Data Ownership
              </h2>
              <p>
                <strong>Your Content:</strong> You retain 100% ownership of all journal entries,
                emotional reflections, assessment answers, and personal profile data you create on
                Soul Sense. We do not claim any ownership rights over your personal reflective
                material.
              </p>
              <p>
                <strong>Soul Sense Platform:</strong> The platform architecture, scoring models,
                algorithms, UI components, brand marks, and software code are the intellectual
                property of Nupur Madaan and the Soul Sense open-source contributors, licensed under
                the repository&apos;s open-source license.
              </p>
            </section>

            {/* Section 4 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">4.</span> Acceptable Use & Prohibited Conduct
              </h2>
              <p>You agree not to engage in any of the following prohibited behaviors:</p>
              <ul className="list-disc pl-6 space-y-2 text-slate-600 dark:text-slate-300">
                <li>
                  Attempting to bypass quota middleware, rate limits, or denial-of-service protections.
                </li>
                <li>
                  Reverse-engineering or attempting to extract decrypted journal entries belonging to other users.
                </li>
                <li>
                  Using automated bots or scraping tools without prior authorization.
                </li>
                <li>
                  Uploading malicious scripts, exploits, or harmful payloads through journal or contact input fields.
                </li>
              </ul>
            </section>

            {/* Section 5 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">5.</span> Data Export & Account Deletion
              </h2>
              <p>
                In alignment with our privacy-first philosophy and GDPR regulations, you may at any time
                export your complete historical data (assessments, EQ breakdowns, journal logs) via our
                Export API in JSON, CSV, or PDF formats. You may also initiate immediate, permanent account
                deletion through your user settings or by contacting our administration team.
              </p>
            </section>

            {/* Section 6 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">6.</span> Limitation of Liability
              </h2>
              <p>
                To the maximum extent permitted by applicable law, Soul Sense, its creator Nupur Madaan,
                and its open-source contributors shall not be liable for any indirect, incidental,
                special, consequential, or punitive damages, or any loss of profits, data, or emotional
                distress arising from your use or inability to use the platform.
              </p>
            </section>

            {/* Section 7 */}
            <section className="space-y-3">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="text-indigo-600 dark:text-indigo-400">7.</span> Governing Law & Contact Information
              </h2>
              <p>
                These Terms shall be governed by and construed in accordance with applicable laws. If
                you have any questions or concerns regarding these Terms, please contact:
              </p>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 space-y-1 text-sm">
                <p className="font-bold text-slate-900 dark:text-white">Soul Sense Legal & Governance</p>
                <p>Lead Maintainer: Nupur Madaan</p>
                <p>
                  Email:{' '}
                  <a href="mailto:nupur.04.m@gmail.com" className="text-indigo-600 dark:text-indigo-400 underline">
                    nupur.04.m@gmail.com
                  </a>
                </p>
                <p>
                  Repository:{' '}
                  <a
                    href="https://github.com/nupurmadaan04/SOUL_SENSE_EXAM"
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-600 dark:text-indigo-400 underline"
                  >
                    github.com/nupurmadaan04/SOUL_SENSE_EXAM
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
