'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HelpCircle,
  Search,
  ChevronDown,
  Brain,
  ShieldCheck,
  BookOpen,
  Sparkles,
  Code2,
  Mail,
  Linkedin,
  Github,
  Twitter,
  ArrowRight,
} from 'lucide-react';
import { Footer, Section } from '@/components/layout';
import { Button } from '@/components/ui';

interface FAQItem {
  id: string;
  category: 'eq' | 'privacy' | 'assessments' | 'journal' | 'tech';
  question: string;
  answer: string;
  tags: string[];
}

const FAQ_DATA: FAQItem[] = [
  {
    id: 'eq-1',
    category: 'eq',
    question: 'What is Emotional Intelligence (EQ) and how does Soul Sense measure it?',
    answer:
      'Emotional Intelligence (EQ) is the capacity to recognize, understand, manage, and reason with our own emotions and the emotions of others. Soul Sense utilizes validated psychometric frameworks across 5 core dimensions: Self-Awareness, Self-Regulation, Intrinsic Motivation, Empathy, and Social Leadership. Our scoring algorithms combine multi-tier Likert psychometrics with sentiment analysis to deliver a nuanced, actionable EQ profile.',
    tags: ['Psychometrics', 'Scoring', 'Core Dimensions'],
  },
  {
    id: 'eq-2',
    category: 'eq',
    question: 'Can emotional intelligence really be improved over time?',
    answer:
      'Yes! Unlike IQ, which remains relatively fixed throughout adulthood, research in neuroplasticity and behavioral psychology demonstrates that emotional intelligence can be significantly cultivated. Through daily guided reflections, cognitive reappraisal exercises, and continuous tracking on Soul Sense, users see measurable improvements in stress recovery, emotional clarity, and interpersonal leadership.',
    tags: ['Growth', 'Neuroplasticity', 'Training'],
  },
  {
    id: 'privacy-1',
    category: 'privacy',
    question: 'How is my private emotional and journal data protected?',
    answer:
      'Soul Sense enforces zero-knowledge architecture and AES-256 GCM client-side encryption. Your reflective entries, mood logs, and psychometric responses are encrypted before persistent storage. We never monetize, sell, or train public AI models on your personal emotional journal data.',
    tags: ['AES-256', 'Zero-Knowledge', 'Security'],
  },
  {
    id: 'privacy-2',
    category: 'privacy',
    question: 'Is Soul Sense compliant with GDPR and international privacy standards?',
    answer:
      'Yes. Soul Sense provides complete GDPR and CCPA compliance. You retain 100% ownership of your data, including the right to export your complete psychological telemetry (JSON, CSV, PDF) and the right to permanently delete your account and associated records with a single click.',
    tags: ['GDPR', 'CCPA', 'Data Export'],
  },
  {
    id: 'assessments-1',
    category: 'assessments',
    question: 'How often should I take the Soul Sense EQ Assessment?',
    answer:
      'We recommend completing a comprehensive assessment once every 2 to 4 weeks, or following major life events and transitions. Daily pulse checks and guided journaling can be completed anytime to provide high-frequency emotional telemetry between formal assessment cycles.',
    tags: ['Cadence', 'Check-in', 'Baseline'],
  },
  {
    id: 'assessments-2',
    category: 'assessments',
    question: 'What happens if I lose internet connection during an assessment?',
    answer:
      'Soul Sense features robust offline session caching. Your answers and in-progress drafts are saved locally in your browser storage and will automatically synchronize with the server as soon as connectivity is restored.',
    tags: ['Offline Mode', 'Auto-Save', 'Reliability'],
  },
  {
    id: 'journal-1',
    category: 'journal',
    question: 'How does the AI sentiment analysis in the journal work?',
    answer:
      'When you write a reflection, our embedded natural language processing models evaluate emotional valence, cognitive framing, and linguistic stress markers. The system provides real-time mood score insights, highlights cognitive distortion patterns, and suggests tailored reframing exercises.',
    tags: ['NLP', 'Sentiment Analysis', 'Reframing'],
  },
  {
    id: 'tech-1',
    category: 'tech',
    question: 'Is Soul Sense open-source and how can I contribute?',
    answer:
      'Yes! Soul Sense is an open-source project created and maintained by Nupur Madaan and our global community of 43+ contributors. You can explore the codebase, report issues, or contribute feature pull requests on our GitHub repository: https://github.com/nupurmadaan04/SOUL_SENSE_EXAM.',
    tags: ['Open Source', 'GitHub', 'Community'],
  },
  {
    id: 'tech-2',
    category: 'tech',
    question: 'Does Soul Sense offer an API for researchers or developers?',
    answer:
      'Yes, Soul Sense exposes over 232 documented OpenAPI / REST endpoints covering assessments, journaling, psychometric statistics, and real-time community pulse telemetry. Check out our interactive API docs at /api/docs or visit our Community page.',
    tags: ['API', 'OpenAPI', 'Developer'],
  },
];

const CATEGORIES = [
  { key: 'all', label: 'All Questions', icon: HelpCircle },
  { key: 'eq', label: 'Emotional Intelligence', icon: Brain },
  { key: 'privacy', label: 'Privacy & Security', icon: ShieldCheck },
  { key: 'assessments', label: 'Assessments', icon: Sparkles },
  { key: 'journal', label: 'Guided Journaling', icon: BookOpen },
  { key: 'tech', label: 'Open Source & Tech', icon: Code2 },
];

export default function FAQPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>('eq-1');

  const filteredFAQs = useMemo(() => {
    return FAQ_DATA.filter((item) => {
      const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;
      const matchesSearch =
        item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.answer.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  const toggleAccordion = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-300">
      <main className="flex-grow pt-28 pb-20">
        <Section className="container mx-auto px-6 max-w-5xl">
          {/* Header Banner */}
          <div className="text-center space-y-4 mb-12">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-bold uppercase tracking-wider"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              Frequently Asked Questions
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 dark:text-white"
            >
              How can we help you thrive?
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto text-base md:text-lg font-normal"
            >
              Explore detailed answers about psychometric frameworks, zero-knowledge privacy,
              assessment algorithms, and open-source contributions.
            </motion.p>

            {/* Search Input */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              className="max-w-xl mx-auto mt-6 relative"
            >
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by keyword, e.g. psychometrics, encryption, API..."
                className="w-full pl-12 pr-4 py-3.5 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-all"
              />
            </motion.div>
          </div>

          {/* Category Tabs */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = selectedCategory === cat.key;
              return (
                <button
                  key={cat.key}
                  onClick={() => setSelectedCategory(cat.key)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'bg-white dark:bg-slate-900/80 border border-slate-200/80 dark:border-white/10 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {cat.label}
                </button>
              );
            })}
          </div>

          {/* FAQ Accordion List */}
          <div className="space-y-4">
            {filteredFAQs.length === 0 ? (
              <div className="p-12 text-center bg-white dark:bg-slate-900/60 rounded-3xl border border-slate-200 dark:border-white/10">
                <HelpCircle className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  No matching questions found
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  Try searching for something else or contact our support directly.
                </p>
              </div>
            ) : (
              filteredFAQs.map((faq, index) => {
                const isOpen = expandedId === faq.id;
                return (
                  <motion.div
                    key={faq.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all"
                  >
                    <button
                      onClick={() => toggleAccordion(faq.id)}
                      className="w-full p-6 text-left flex items-start justify-between gap-4 focus:outline-none"
                    >
                      <span className="font-bold text-base md:text-lg text-slate-900 dark:text-white leading-snug">
                        {faq.question}
                      </span>
                      <div
                        className={`p-2 rounded-full transition-transform duration-300 flex-shrink-0 ${
                          isOpen
                            ? 'bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 rotate-180'
                            : 'bg-slate-100 dark:bg-white/5 text-slate-500'
                        }`}
                      >
                        <ChevronDown className="w-4 h-4" />
                      </div>
                    </button>

                    <AnimatePresence>
                      {isOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.3 }}
                          className="overflow-hidden"
                        >
                          <div className="px-6 pb-6 pt-1 border-t border-slate-100 dark:border-white/5">
                            <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm md:text-base font-normal">
                              {faq.answer}
                            </p>
                            <div className="flex flex-wrap gap-2 mt-4">
                              {faq.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-white/5"
                                >
                                  #{tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })
            )}
          </div>

          {/* Still Have Questions Contact Card */}
          <div className="mt-16 p-8 md:p-10 rounded-3xl bg-gradient-to-br from-indigo-900 to-slate-900 text-white relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="space-y-3 text-center md:text-left">
                <span className="text-xs font-bold uppercase tracking-widest text-indigo-300">
                  Direct Community & Creator Support
                </span>
                <h3 className="text-2xl md:text-3xl font-black">Still have questions?</h3>
                <p className="text-slate-300 text-sm max-w-xl">
                  Reach out directly to creator & lead architect <strong>Nupur Madaan</strong> or join
                  our active community discussion.
                </p>
                <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 pt-2">
                  <a
                    href="mailto:nupur.04.m@gmail.com"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white transition-colors"
                  >
                    <Mail className="w-4 h-4" /> nupur.04.m@gmail.com
                  </a>
                  <a
                    href="https://www.linkedin.com/in/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white transition-colors"
                  >
                    <Linkedin className="w-4 h-4" /> LinkedIn Profile
                  </a>
                  <a
                    href="https://github.com/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white transition-colors"
                  >
                    <Github className="w-4 h-4" /> @nupurmadaan04
                  </a>
                  <a
                    href="https://twitter.com/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white transition-colors"
                  >
                    <Twitter className="w-4 h-4" /> @nupurmadaan04
                  </a>
                </div>
              </div>
              <Link href="/contact" className="flex-shrink-0">
                <Button className="bg-white text-slate-950 hover:bg-slate-100 font-bold px-6 py-3 rounded-full shadow-lg flex items-center gap-2">
                  Contact Us
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>
        </Section>
      </main>

      <Footer />
    </div>
  );
}
