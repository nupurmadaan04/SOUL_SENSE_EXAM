'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Mail,
  Linkedin,
  Github,
  Twitter,
  Send,
  CheckCircle2,
  MapPin,
  Clock,
  Sparkles,
  MessageSquare,
  HelpCircle,
  ArrowRight,
} from 'lucide-react';
import { Footer, Section } from '@/components/layout';
import { Button } from '@/components/ui';

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: 'General Inquiry',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSubmitted(true);
    }, 1000);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-300">
      <main className="flex-grow pt-28 pb-20">
        <Section className="container mx-auto px-6 max-w-6xl">
          {/* Header Banner */}
          <div className="text-center space-y-4 mb-14">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-bold uppercase tracking-wider"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Get In Touch
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 dark:text-white"
            >
              Let&apos;s build a more mindful world.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto text-base md:text-lg"
            >
              Have a question about Soul Sense, research collaboration, enterprise psychometrics, or
              open-source features? Connect with us directly.
            </motion.p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Creator Profile & Social Hub */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="lg:col-span-5 space-y-6"
            >
              {/* Creator Card */}
              <div className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-3xl p-8 shadow-sm">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-black text-2xl shadow-md">
                    NM
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                      Nupur Madaan
                    </h2>
                    <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                      Lead Architect & Creator
                    </p>
                    <span className="text-xs text-slate-500">SOUL_SENSE_EXAM Project</span>
                  </div>
                </div>

                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-6 font-normal">
                  Open-source developer and psychometrics researcher building privacy-preserving,
                  AI-assisted emotional intelligence tools for individuals and high-performance
                  teams.
                </p>

                {/* Direct Links */}
                <div className="space-y-3">
                  <a
                    href="mailto:nupur.04.m@gmail.com"
                    className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 hover:border-indigo-500/40 transition-all text-slate-700 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 text-sm font-medium group"
                  >
                    <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group-hover:scale-110 transition-transform">
                      <Mail className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[10px] text-slate-400 font-bold uppercase">Direct Email</span>
                      <span className="truncate">nupur.04.m@gmail.com</span>
                    </div>
                  </a>

                  <a
                    href="https://www.linkedin.com/in/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 hover:border-blue-500/40 transition-all text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-sm font-medium group"
                  >
                    <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform">
                      <Linkedin className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[10px] text-slate-400 font-bold uppercase">LinkedIn</span>
                      <span className="truncate">linkedin.com/in/nupurmadaan04</span>
                    </div>
                  </a>

                  <a
                    href="https://github.com/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 hover:border-slate-500/40 transition-all text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white text-sm font-medium group"
                  >
                    <div className="p-2 rounded-xl bg-slate-100 dark:bg-white/10 text-slate-700 dark:text-slate-200 group-hover:scale-110 transition-transform">
                      <Github className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[10px] text-slate-400 font-bold uppercase">GitHub Profile</span>
                      <span className="truncate">github.com/nupurmadaan04</span>
                    </div>
                  </a>

                  <a
                    href="https://twitter.com/nupurmadaan04"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 hover:border-sky-500/40 transition-all text-slate-700 dark:text-slate-200 hover:text-sky-500 text-sm font-medium group"
                  >
                    <div className="p-2 rounded-xl bg-sky-50 dark:bg-sky-500/10 text-sky-500 group-hover:scale-110 transition-transform">
                      <Twitter className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[10px] text-slate-400 font-bold uppercase">Twitter / X</span>
                      <span className="truncate">@nupurmadaan04</span>
                    </div>
                  </a>
                </div>
              </div>

              {/* Quick FAQ Link Card */}
              <div className="bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-500/20 rounded-3xl p-6 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-indigo-950 dark:text-indigo-200">
                    Looking for instant answers?
                  </h3>
                  <p className="text-xs text-indigo-700 dark:text-indigo-400 mt-0.5">
                    Check our FAQ section for common questions.
                  </p>
                </div>
                <Link href="/faq">
                  <Button size="sm" className="rounded-full bg-indigo-600 text-white hover:bg-indigo-700">
                    View FAQ
                  </Button>
                </Link>
              </div>
            </motion.div>

            {/* Right Column: Interactive Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              className="lg:col-span-7"
            >
              <div className="bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-3xl p-8 md:p-10 shadow-sm">
                {isSubmitted ? (
                  <div className="text-center py-12 space-y-4">
                    <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white">
                      Message Received!
                    </h3>
                    <p className="text-slate-600 dark:text-slate-300 max-w-md mx-auto text-sm">
                      Thank you for reaching out. We have received your inquiry and will respond to{' '}
                      <strong>{formData.email}</strong> within 24–48 hours.
                    </p>
                    <Button
                      onClick={() => {
                        setIsSubmitted(false);
                        setFormData({ name: '', email: '', subject: 'General Inquiry', message: '' });
                      }}
                      className="mt-6 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900"
                    >
                      Send Another Message
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="space-y-1">
                      <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                        Send us a message
                      </h2>
                      <p className="text-xs text-slate-500">
                        Fill out the details below and we&apos;ll get back to you promptly.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                          Your Name
                        </label>
                        <input
                          type="text"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder="e.g. Jane Doe"
                          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                          Email Address
                        </label>
                        <input
                          type="email"
                          required
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="e.g. jane@example.com"
                          className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                        Subject / Topic
                      </label>
                      <select
                        value={formData.subject}
                        onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                        className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="General Inquiry">General Inquiry</option>
                        <option value="Research & Psychometrics">Research & Psychometrics</option>
                        <option value="Open Source & Contributing">Open Source & Contributing</option>
                        <option value="Bug Report / Security">Bug Report / Security Vulnerability</option>
                        <option value="Partnership / Enterprise">Partnership / Enterprise</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                        Message Content
                      </label>
                      <textarea
                        required
                        rows={5}
                        value={formData.message}
                        onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                        placeholder="Tell us how we can assist you with Soul Sense..."
                        className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                      />
                    </div>

                    <Button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2"
                    >
                      {isSubmitting ? (
                        <span>Sending message...</span>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          <span>Send Message</span>
                        </>
                      )}
                    </Button>
                  </form>
                )}
              </div>
            </motion.div>
          </div>
        </Section>
      </main>

      <Footer />
    </div>
  );
}
