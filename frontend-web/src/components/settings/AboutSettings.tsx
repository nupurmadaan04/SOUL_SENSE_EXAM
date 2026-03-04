'use client';

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
} from 'lucide-react';

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

  const handleOpenGitHub = () => {
    window.open('https://github.com/your-org/soul-sense-exam', '_blank');
  };

  const handleOpenDocs = () => {
    window.open('/docs', '_blank');
  };

  const handleContactSupport = () => {
    window.open('mailto:support@soulsense.com', '_blank');
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
                className="h-9 px-6 rounded-full font-black uppercase tracking-widest text-[10px] border-border/60"
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
            className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 hover:bg-muted/10 hover:border-primary/20 transition-all text-center"
          >
            <Github className="h-5 w-5 text-muted-foreground" />
            <p className="text-[10px] font-black uppercase tracking-widest">Star Repo</p>
          </button>
          <div className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 text-center">
            <MessageSquare className="h-5 w-5 text-muted-foreground" />
            <p className="text-[10px] font-black uppercase tracking-widest">Report Bug</p>
          </div>
          <div className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 text-center">
            <BookOpen className="h-5 w-5 text-muted-foreground" />
            <p className="text-[10px] font-black uppercase tracking-widest">Contribute</p>
          </div>
          <div className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-muted/5 border border-border/40 text-center">
            <Star className="h-5 w-5 text-muted-foreground" />
            <p className="text-[10px] font-black uppercase tracking-widest">Spread Word</p>
          </div>
        </div>
      </div>
    </div>
  );
}
