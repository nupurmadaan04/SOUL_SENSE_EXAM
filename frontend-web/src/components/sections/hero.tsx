import { motion } from 'framer-motion';
import { Button } from '@/components/ui';
import Link from 'next/link';
import { 
  ArrowRight, 
  Sparkles, 
  Brain, 
  Activity, 
  Heart, 
  Zap, 
  ShieldCheck, 
  TrendingUp, 
  Compass,
  CheckCircle2
} from 'lucide-react';
import { Section } from '@/components/layout';
import { analytics } from '@/lib/utils/analytics';
import { useAuth } from '@/hooks/useAuth';

export function Hero() {
  const { isAuthenticated } = useAuth();

  const eqDimensions = [
    { name: 'Self-Awareness', score: 92, label: 'Exceptional', color: 'from-emerald-500 to-teal-400', desc: 'Accurate recognition of internal emotional states' },
    { name: 'Self-Regulation', score: 88, label: 'High Mastery', color: 'from-blue-500 to-cyan-400', desc: 'Constructive emotional redirection under pressure' },
    { name: 'Intrinsic Motivation', score: 95, label: 'Peak Drive', color: 'from-indigo-500 to-violet-400', desc: 'Deep resilience and purpose-oriented orientation' },
    { name: 'Empathy & Resonance', score: 90, label: 'Empathetic', color: 'from-purple-500 to-pink-400', desc: 'Nuanced understanding of nonverbal & social cues' },
    { name: 'Social Leadership', score: 86, label: 'Advanced', color: 'from-amber-500 to-orange-400', desc: 'Collaborative influence and conflict mitigation' },
  ];

  return (
    <Section className="pt-32 lg:pt-48 overflow-hidden relative">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/20 blur-[120px] rounded-full" />
      </div>

      <div className="flex flex-col items-center text-center gap-8 max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border bg-background/50 backdrop-blur-sm text-sm font-medium text-primary shadow-sm"
        >
          <Sparkles className="h-4 w-4" />
          <span>Unlock Your Emotional Potential</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]"
        >
          Decode Your Emotions with{' '}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-primary bg-[length:200%_auto] animate-gradient">
            Soul Sense
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-xl text-muted-foreground leading-relaxed max-w-2xl"
        >
          Step into a world of self-awareness. Our AI-powered emotional intelligence test provides
          deep insights into your feelings, helping you build better relationships and a stronger
          mind.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
        >
          <Button
            size="lg"
            className="h-14 px-8 rounded-full text-lg group bg-gradient-to-r from-primary to-secondary"
            asChild
            onClick={() => analytics.trackButtonClick('hero_start_free_test', 'button')}
          >
            <Link href={isAuthenticated ? '/dashboard' : '/register'}>
              Start Free EQ Test
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="h-14 px-8 rounded-full text-lg"
            asChild
            onClick={() => analytics.trackButtonClick('hero_learn_more', 'button')}
          >
            <Link href="#features">Learn How It Works</Link>
          </Button>
        </motion.div>

        {/* Real-Time EQ Telemetry Showcase Dashboard */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="mt-12 relative w-full max-w-5xl rounded-3xl border border-border/80 bg-card/60 backdrop-blur-xl p-6 sm:p-8 shadow-2xl overflow-hidden text-left"
        >
          {/* Ambient Glows */}
          <div className="absolute top-0 right-1/4 w-96 h-96 bg-primary/15 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-secondary/15 rounded-full blur-3xl pointer-events-none" />

          {/* Telemetry Header */}
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-border/60">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-primary/10 border border-primary/20 text-primary">
                <Brain className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-lg text-foreground">Real-time EQ Psychometric Telemetry</h3>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    LIVE ENGINE
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Neural EQ Assessment Engine • Session #SS-8942-ACT</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="bg-background/60 border border-border/80 rounded-2xl px-4 py-2 flex items-center gap-3">
                <div className="text-right">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Composite EQ</div>
                  <div className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">132 / 150</div>
                </div>
                <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                  96th%
                </div>
              </div>
            </div>
          </div>

          {/* Core Content Grid */}
          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
            {/* Left 5-Dimension Spectrum (5 cols) */}
            <div className="lg:col-span-5 space-y-3.5 flex flex-col justify-center">
              <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1">
                <span>Core EQ Dimensions</span>
                <span>Proficiency</span>
              </div>
              
              {eqDimensions.map((dim, idx) => (
                <motion.div
                  key={dim.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + idx * 0.1 }}
                  className="p-3 rounded-xl bg-background/50 border border-border/60 hover:border-primary/40 transition-all group"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">{dim.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-muted-foreground">{dim.label}</span>
                      <span className="text-xs font-bold text-foreground font-mono">{dim.score}%</span>
                    </div>
                  </div>
                  <div className="w-full h-2 rounded-full bg-muted/60 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${dim.score}%` }}
                      transition={{ duration: 1.2, delay: 0.6 + idx * 0.1, ease: "easeOut" }}
                      className={`h-full rounded-full bg-gradient-to-r ${dim.color}`}
                    />
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Middle Real-time Biometric / Neural Waveform Card (4 cols) */}
            <div className="lg:col-span-4 rounded-2xl bg-gradient-to-b from-background/70 to-background/40 border border-border/60 p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5 text-primary" />
                    Emotional Resonance
                  </span>
                  <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded-md">
                    Harmonious
                  </span>
                </div>

                {/* Animated Waveform SVG */}
                <div className="h-28 w-full relative flex items-center justify-center my-2 overflow-hidden rounded-xl bg-muted/20 border border-border/40 p-2">
                  <svg className="w-full h-full" viewBox="0 0 300 80" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="waveGradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.8" />
                        <stop offset="50%" stopColor="#8B5CF6" stopOpacity="1" />
                        <stop offset="100%" stopColor="#10B981" stopOpacity="0.8" />
                      </linearGradient>
                      <linearGradient id="waveFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 0,40 Q 35,15 70,40 T 140,40 T 210,40 T 280,40 T 350,40 L 350,80 L 0,80 Z"
                      fill="url(#waveFill)"
                    />
                    <path
                      d="M 0,40 Q 35,15 70,40 T 140,40 T 210,40 T 280,40 T 350,40"
                      fill="none"
                      stroke="url(#waveGradient)"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/10 to-transparent animate-pulse" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border/40">
                <div className="p-2.5 rounded-xl bg-background/60 border border-border/40">
                  <div className="text-[10px] text-muted-foreground uppercase font-semibold">Stress Recovery</div>
                  <div className="text-lg font-bold text-foreground flex items-center gap-1 font-mono">
                    <Heart className="h-4 w-4 text-rose-500" />
                    94%
                  </div>
                </div>
                <div className="p-2.5 rounded-xl bg-background/60 border border-border/40">
                  <div className="text-[10px] text-muted-foreground uppercase font-semibold">Mindful Focus</div>
                  <div className="text-lg font-bold text-foreground flex items-center gap-1 font-mono">
                    <Zap className="h-4 w-4 text-amber-500" />
                    89%
                  </div>
                </div>
              </div>
            </div>

            {/* Right Dynamic AI Insights Panel (3 cols) */}
            <div className="lg:col-span-3 rounded-2xl bg-gradient-to-b from-background/70 to-background/40 border border-border/60 p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1 rounded-md bg-secondary/10 text-secondary">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                  <span className="text-xs font-bold text-foreground uppercase tracking-wider">AI Diagnostic</span>
                </div>
                <div className="text-xs text-muted-foreground leading-relaxed mb-4">
                  High internal motivation and emotional regulation under pressure. Outstanding empathy quotient for leadership scenarios.
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Deep Reflective Capacity</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Adaptive Stress Resilience</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Empathetic Communication</span>
                </div>
                <div className="mt-3 pt-3 border-t border-border/40 flex items-center justify-between text-[11px] font-medium text-primary">
                  <span className="flex items-center gap-1">
                    <Compass className="h-3.5 w-3.5" />
                    Psychometric Model v3.4
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Active Banner */}
          <div className="relative z-10 mt-6 pt-4 border-t border-border/40 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
              <span className="font-medium text-foreground">Real-time EQ Analysis Active</span>
              <span>— Psychometrically validated based on Goleman & Mayer-Salovey models</span>
            </div>
            <div className="font-mono text-[11px] text-muted-foreground">
              Encrypted Telemetry • AES-256 GCM
            </div>
          </div>
        </motion.div>
      </div>
    </Section>
  );
}
