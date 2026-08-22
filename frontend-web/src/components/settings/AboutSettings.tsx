'use client';

import { useState } from 'react';
import { Button } from '@/components/ui';
import {
  Heart,
  Github,
  ExternalLink,
  Info,
  Code,
  Users,
  Star,
  MessageSquare,
  BookOpen,
  Layers,
  Share2,
  Check,
  Copy,
  Send,
  X,
} from 'lucide-react';
import { toast } from '@/lib/toast';

interface AboutSettingsProps {
  onRestartTutorial?: () => void;
}

export function AboutSettings({ onRestartTutorial }: AboutSettingsProps) {
  const version = '1.0.0';
  const buildDate = new Date().toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const [isBugModalOpen, setIsBugModalOpen] = useState(false);
  const [bugSubject, setBugSubject] = useState('');
  const [bugDescription, setBugDescription] = useState('');
  const [bugCategory, setBugCategory] = useState('UI / Display Issue');
  const [copiedLink, setCopiedLink] = useState(false);

  const handleOpenGitHub = () => {
    window.open('https://github.com/nupurmadaan04/SOUL_SENSE_EXAM', '_blank');
  };

  const handleOpenDocs = () => {
    window.open('/docs', '_blank');
  };

  const handleContactSupport = () => {
    window.open('mailto:nupur.04.mn@gmail.com?subject=Soul%20Sense%20Support', '_blank');
  };

  const handleSendBugReport = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bugDescription.trim()) {
      toast.error('Please provide a description of the issue.');
      return;
    }
    const subject = encodeURIComponent(`[Bug Report] ${bugCategory}: ${bugSubject || 'Issue Encountered'}`);
    const body = encodeURIComponent(
      `Bug Report Details:\n\nCategory: ${bugCategory}\nSubject: ${bugSubject}\n\nDescription:\n${bugDescription}\n\nApp Version: ${version}\nDate: ${buildDate}`
    );
    window.open(`mailto:nupur.04.mn@gmail.com?subject=${subject}&body=${body}`, '_blank');
    toast.success('Opening email client to send bug report to nupur.04.mn@gmail.com');
    setIsBugModalOpen(false);
    setBugSubject('');
    setBugDescription('');
  };

  const handleSpreadWord = async () => {
    const shareUrl = typeof window !== 'undefined' ? window.location.origin : 'https://soulsense.app';
    const shareTitle = 'Soul Sense - AI-Powered Emotional Intelligence Test';
    const shareText = 'Discover and elevate your emotional intelligence with Soul Sense!';

    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({
          title: shareTitle,
          text: shareText,
          url: shareUrl,
        });
        toast.success('Thank you for spreading the word!');
        return;
      } catch (err) {
        // Fallback to clipboard if user dismissed or cancelled share dialog
      }
    }

    try {
      await navigator.clipboard.writeText(`${shareTitle} - ${shareUrl}`);
      setCopiedLink(true);
      toast.success('Link copied to clipboard! Thank you for sharing Soul Sense.');
      setTimeout(() => setCopiedLink(false), 3000);
    } catch {
      toast.info(`Share Soul Sense: ${shareUrl}`);
    }
  };

  return (
    <div className="space-y-12">
      {/* App Information Cluster */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Info className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">System Identity</h3>
        </div>

        <div className="p-8 bg-primary/5 border border-primary/20 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity">
            <Layers className="h-32 w-32 rotate-12" />
          </div>

          <div className="relative z-10 space-y-6">
            <div className="space-y-1">
              <h4 className="text-2xl font-black tracking-tight">
                Soul Sense <span className="text-primary/60">Exam</span>
              </h4>
              <p className="text-muted-foreground text-xs font-medium">
                Advanced Emotional Intelligence Infrastructure
              </p>
            </div>

            <div className="flex flex-wrap gap-8">
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/40 mb-1">
                  Version
                </p>
                <p className="font-bold text-sm tracking-tight">{version}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-widest font-black text-muted-foreground/40 mb-1">
                  Release Cycle
                </p>
                <p className="font-bold text-sm tracking-tight">{buildDate}</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                onClick={handleOpenDocs}
                size="sm"
                className="h-9 px-6 rounded-full font-black uppercase tracking-widest text-[10px]"
              >
                <BookOpen className="h-3 w-3 mr-2" />
                Documentation
              </Button>
              <Button
                onClick={handleContactSupport}
                variant="outline"
                size="sm"
                className="h-9 px-6 rounded-full font-black uppercase tracking-widest text-[10px] border-border/60 hover:border-primary/40 hover:text-primary"
              >
                <Heart className="h-3 w-3 mr-2 text-rose-500" />
                Get Support
              </Button>
              {onRestartTutorial && (
                <Button
                  onClick={onRestartTutorial}
                  variant="outline"
                  size="sm"
                  className="h-9 px-6 rounded-full font-black uppercase tracking-widest text-[10px] border-border/60"
                >
                  <Star className="h-3 w-3 mr-2 text-yellow-500" />
                  Restart Tutorial
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Engineering Foundations */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Code className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Engineering Stacks</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-6 bg-muted/10 border border-border/40 rounded-2xl space-y-4">
            <p className="text-xs font-black uppercase tracking-widest text-muted-foreground/60">
              Core Technologies
            </p>
            <div className="grid grid-cols-2 gap-y-3">
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold">Frontend</p>
                <p className="text-[9px] text-muted-foreground font-medium uppercase tracking-tight">
                  Next.js & TypeScript
                </p>
              </div>
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold">Backend</p>
                <p className="text-[9px] text-muted-foreground font-medium uppercase tracking-tight">
                  FastAPI & Python
                </p>
              </div>
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold">Database</p>
                <p className="text-[9px] text-muted-foreground font-medium uppercase tracking-tight">
                  PostgreSQL Cluster
                </p>
              </div>
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold">Inference</p>
                <p className="text-[9px] text-muted-foreground font-medium uppercase tracking-tight">
                  Transformers & Sci-Kit
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 bg-muted/10 border border-border/40 rounded-2xl space-y-4">
            <p className="text-xs font-black uppercase tracking-widest text-muted-foreground/60">
              Legal & Licensing
            </p>
            <p className="text-[11px] text-muted-foreground leading-relaxed font-medium">
              Licensed under MIT. Openly available for modification and distribution worldwide.
            </p>
            <Button
              onClick={() => window.open('https://github.com/nupurmadaan04/SOUL_SENSE_EXAM/blob/main/LICENSE', '_blank')}
              variant="link"
              className="p-0 h-auto text-[10px] font-black uppercase tracking-widest text-primary/80 hover:text-primary"
            >
              Read License Agreement
              <ExternalLink className="h-2.5 w-2.5 ml-1.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Community Contribution */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-muted-foreground/60">
          <Users className="h-3.5 w-3.5" />
          <h3 className="text-[10px] uppercase tracking-widest font-black">Community Sync</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <button
            onClick={handleOpenGitHub}
            className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 hover:bg-muted/15 hover:border-primary/30 transition-all text-center group active:scale-98"
          >
            <Github className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            <p className="text-[10px] font-black uppercase tracking-widest group-hover:text-foreground">Star Repo</p>
          </button>

          <button
            onClick={() => setIsBugModalOpen(true)}
            className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 hover:bg-muted/15 hover:border-primary/30 transition-all text-center group active:scale-98"
          >
            <MessageSquare className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            <p className="text-[10px] font-black uppercase tracking-widest group-hover:text-foreground">Report Bug</p>
          </button>

          <button
            onClick={handleOpenGitHub}
            className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 hover:bg-muted/15 hover:border-primary/30 transition-all text-center group active:scale-98"
          >
            <BookOpen className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            <p className="text-[10px] font-black uppercase tracking-widest group-hover:text-foreground">Contribute</p>
          </button>

          <button
            onClick={handleSpreadWord}
            className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 hover:bg-muted/15 hover:border-primary/30 transition-all text-center group active:scale-98"
          >
            {copiedLink ? (
              <Check className="h-5 w-5 text-emerald-500 animate-pulse" />
            ) : (
              <Share2 className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
            )}
            <p className="text-[10px] font-black uppercase tracking-widest group-hover:text-foreground">
              {copiedLink ? 'Link Copied!' : 'Spread Word'}
            </p>
          </button>
        </div>
      </div>

      {/* REPORT BUG DIALOG MODAL */}
      {isBugModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in">
          <div className="relative w-full max-w-lg rounded-3xl border border-border/80 bg-card/95 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-border/40 pb-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground">Report a Bug / Feedback</h3>
                  <p className="text-xs text-muted-foreground">Directly sent to nupur.04.mn@gmail.com</p>
                </div>
              </div>
              <button
                onClick={() => setIsBugModalOpen(false)}
                className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSendBugReport} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Category
                </label>
                <select
                  value={bugCategory}
                  onChange={(e) => setBugCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-background text-foreground border border-border/80 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary"
                >
                  <option value="UI / Display Issue">UI / Display Issue</option>
                  <option value="Assessment or Scoring Question">Assessment or Scoring Question</option>
                  <option value="Profile & Settings Save">Profile & Settings Save</option>
                  <option value="Authentication & Login">Authentication & Login</option>
                  <option value="Other Feature Request">Other Feature Request</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Issue Summary
                </label>
                <input
                  type="text"
                  value={bugSubject}
                  onChange={(e) => setBugSubject(e.target.value)}
                  placeholder="Brief headline of the issue..."
                  className="w-full px-3.5 py-2.5 bg-background text-foreground border border-border/80 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-muted-foreground/60"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Description & Steps to Reproduce
                </label>
                <textarea
                  rows={4}
                  value={bugDescription}
                  onChange={(e) => setBugDescription(e.target.value)}
                  placeholder="Explain what happened, what was expected, and any error message..."
                  className="w-full px-3.5 py-2.5 bg-background text-foreground border border-border/80 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-muted-foreground/60 resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border/40">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsBugModalOpen(false)}
                  className="rounded-xl px-5 text-xs font-bold uppercase tracking-wider"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="rounded-xl px-6 text-xs font-bold uppercase tracking-wider gap-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20"
                >
                  <Send className="h-3.5 w-3.5" />
                  Send Bug Report
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
