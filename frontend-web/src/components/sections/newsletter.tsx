'use client';

import React from 'react';
import { Section } from '@/components/layout';
import { Button, Input } from '@/components/ui';
import { Mail, CheckCircle2 } from 'lucide-react';

export function Newsletter() {
  const [email, setEmail] = React.useState('');
  const [status, setStatus] = React.useState<'idle' | 'loading' | 'success'>('idle');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus('loading');
    // Simulate API call
    setTimeout(() => {
      setStatus('success');
      setEmail('');
    }, 1500);
  };

  return (
    <Section className="bg-primary/5">
      <div className="max-w-4xl mx-auto p-8 lg:p-12 rounded-3xl bg-background border shadow-xl relative overflow-hidden">
        {/* Abstract shape */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/2" />

        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 text-primary font-semibold">
              <Mail className="h-5 w-5" />
              <span>Monthly EQ Digest</span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight">
              Stay ahead of the emotional curve.
            </h2>
            <p className="text-muted-foreground">
              Get exclusive EQ tips, research, and early access to new Soul Sense features delivered
              to your inbox.
            </p>
          </div>

          <div>
            {status === 'success' ? (
              <div className="flex flex-col items-center text-center gap-4 py-8 animate-in fade-in zoom-in">
                <div className="h-16 w-16 rounded-full bg-green-500/10 flex items-center justify-center">
                  <CheckCircle2 className="h-8 w-8 text-green-500" />
                </div>
                <h3 className="text-xl font-bold">You&apos;re on the list!</h3>
                <p className="text-muted-foreground">Check your email for a welcome gift.</p>
                <Button variant="outline" onClick={() => setStatus('idle')}>
                  Close
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div className="space-y-2">
                  <Input
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="h-12 text-lg px-4"
                  />
                  <p className="text-xs text-muted-foreground">
                    We value your privacy. Unsubscribe at any time.
                  </p>
                </div>
                <Button
                  type="submit"
                  size="lg"
                  className="h-12 text-lg bg-gradient-to-r from-primary to-secondary"
                  disabled={status === 'loading'}
                >
                  {status === 'loading' ? 'Joining...' : 'Subscribe Now'}
                </Button>
              </form>
            )}
          </div>
        </div>
      </div>
    </Section>
  );
}
