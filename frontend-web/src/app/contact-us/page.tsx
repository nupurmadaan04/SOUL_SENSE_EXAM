'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Send, Loader2, Mail, User, MessageSquare, FileText, CheckCircle } from 'lucide-react';
import { Form, FormField } from '@/components/forms';
import { Button, Input } from '@/components/ui';
import { Footer, Section } from '@/components/layout';
import { contactSchema } from '@/lib/validation';
import { z } from 'zod';

type ContactFormData = z.infer<typeof contactSchema>;

export default function ContactUsPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: ContactFormData) => {
    setIsLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/contact/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Failed to submit form');
      }

      const result = await response.json();
      console.log('Contact form submitted:', result);
      setIsSuccess(true);
    } catch (err) {
      console.error('Contact form error:', err);
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setIsSuccess(false);
    setError(null);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-grow">
        {/* Hero Section */}
        <Section className="pt-32 lg:pt-48 overflow-hidden relative min-h-screen flex flex-col justify-center">
          {/* Background Effects matching Hero style */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 pointer-events-none">
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full animate-pulse" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/20 blur-[120px] rounded-full" />
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 via-transparent to-secondary/5" />
          </div>

          <div className="container mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center mb-12"
            >
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight mb-4">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                  Get in Touch
                </span>
              </h1>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                Have questions about Soul Sense? We&apos;d love to hear from you. Send us a message
                and we&apos;ll respond as soon as possible.
              </p>
            </motion.div>

            <div className="max-w-2xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="glass-card p-8 md:p-10 border-white/10"
              >
                {isSuccess ? (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-8"
                  >
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-6">
                      <CheckCircle className="w-8 h-8 text-green-500" />
                    </div>
                    <h2 className="text-2xl font-semibold mb-3">Message Sent!</h2>
                    <p className="text-muted-foreground mb-6">
                      Thank you for reaching out. We&apos;ll get back to you as soon as possible.
                    </p>
                    <Button onClick={handleReset} variant="outline" className="rounded-full px-6">
                      Send Another Message
                    </Button>
                  </motion.div>
                ) : (
                  <Form schema={contactSchema} onSubmit={handleSubmit} className="space-y-6">
                    {(methods) => (
                      <>
                        <motion.div
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.2 }}
                        >
                          <FormField
                            control={methods.control}
                            name="name"
                            label="Full Name"
                            required
                          >
                            {(fieldProps) => (
                              <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                  {...fieldProps}
                                  placeholder="Your full name"
                                  className="pl-10"
                                />
                              </div>
                            )}
                          </FormField>
                        </motion.div>

                        <motion.div
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.25 }}
                        >
                          <FormField
                            control={methods.control}
                            name="email"
                            label="Email Address"
                            required
                          >
                            {(fieldProps) => (
                              <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                  {...fieldProps}
                                  type="email"
                                  placeholder="you@example.com"
                                  className="pl-10"
                                />
                              </div>
                            )}
                          </FormField>
                        </motion.div>

                        <motion.div
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.3 }}
                        >
                          <FormField
                            control={methods.control}
                            name="subject"
                            label="Subject"
                            required
                          >
                            {(fieldProps) => (
                              <div className="relative">
                                <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                  {...fieldProps}
                                  placeholder="How can we help?"
                                  className="pl-10"
                                />
                              </div>
                            )}
                          </FormField>
                        </motion.div>

                        <motion.div
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.35 }}
                        >
                          <FormField
                            control={methods.control}
                            name="message"
                            label="Message"
                            required
                          >
                            {(fieldProps) => (
                              <div className="relative">
                                <MessageSquare className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                <textarea
                                  {...fieldProps}
                                  placeholder="Tell us more about your inquiry..."
                                  rows={5}
                                  className="w-full pl-10 pr-4 py-3 rounded-md border bg-background text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary resize-none"
                                />
                              </div>
                            )}
                          </FormField>
                        </motion.div>

                        {error && (
                          <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="p-4 rounded-lg bg-destructive/10 border border-destructive/20"
                          >
                            <p className="text-sm text-destructive">{error}</p>
                          </motion.div>
                        )}

                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.4 }}
                        >
                          <Button
                            type="submit"
                            disabled={isLoading}
                            className="w-full h-12 bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity rounded-full text-base font-medium"
                          >
                            {isLoading ? (
                              <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Sending...
                              </>
                            ) : (
                              <>
                                <Send className="mr-2 h-5 w-5" />
                                Send Message
                              </>
                            )}
                          </Button>
                        </motion.div>

                        <motion.p
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 0.45 }}
                          className="text-center text-sm text-muted-foreground"
                        >
                          By submitting this form, you agree to our{' '}
                          <Link
                            href="/privacy"
                            className="text-primary hover:text-primary/80 transition-colors"
                          >
                            Privacy Policy
                          </Link>
                        </motion.p>
                      </>
                    )}
                  </Form>
                )}
              </motion.div>

              {/* Contact Info Cards */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12"
              >
                <div className="glass-card p-6 text-center card-hover">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
                    <Mail className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">Direct Email</h3>
                  <a
                    href="mailto:nupur.04.m@gmail.com"
                    className="text-sm text-primary hover:underline"
                  >
                    nupur.04.m@gmail.com
                  </a>
                </div>
                <div className="glass-card p-6 text-center card-hover">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-secondary/10 mb-4">
                    <MessageSquare className="w-6 h-6 text-secondary" />
                  </div>
                  <h3 className="font-semibold mb-2">Creator Connect</h3>
                  <div className="flex items-center justify-center gap-4 mt-2">
                    <a
                      href="https://www.linkedin.com/in/nupurmadaan04"
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted-foreground hover:text-primary font-medium"
                    >
                      LinkedIn
                    </a>
                    <span>•</span>
                    <a
                      href="https://github.com/nupurmadaan04"
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted-foreground hover:text-primary font-medium"
                    >
                      GitHub
                    </a>
                    <span>•</span>
                    <a
                      href="https://twitter.com/nupurmadaan04"
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted-foreground hover:text-primary font-medium"
                    >
                      Twitter
                    </a>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
