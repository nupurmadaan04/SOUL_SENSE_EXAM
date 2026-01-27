'use client';

import { motion } from 'framer-motion';
import { Brain, Target, Zap, Heart, MessageCircle, BarChart3 } from 'lucide-react';
import { Section } from '@/components/layout';

const features = [
  {
    name: 'AI-Powered Analysis',
    description:
      'Our advanced algorithms analyze your responses to provide a precise mapping of your emotional landscape.',
    icon: Brain,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
  },
  {
    name: 'Actionable Insights',
    description:
      'Receive personalized recommendations and exercises to strengthen your EQ in areas that matter most.',
    icon: Target,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
  },
  {
    name: 'Real-time Feedback',
    description:
      'Get immediate results and track your emotional growth over time with intuitive progress dashboards.',
    icon: Zap,
    color: 'text-yellow-500',
    bg: 'bg-yellow-500/10',
  },
  {
    name: 'Relationship Mapping',
    description:
      'Understand how your EQ affects your interactions and learn strategies for healthier connections.',
    icon: Heart,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
  },
  {
    name: 'Communication Coaching',
    description:
      'Master the art of expression with tips tailored to your unique emotional profile and communication style.',
    icon: MessageCircle,
    color: 'text-green-500',
    bg: 'bg-green-500/10',
  },
  {
    name: 'Workplace Dynamics',
    description:
      'Boost your professional success by mastering empathy, leadership, and stress management skills.',
    icon: BarChart3,
    color: 'text-indigo-500',
    bg: 'bg-indigo-500/10',
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export function Features() {
  return (
    <Section id="features" className="bg-accent/5">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h2 className="text-3xl lg:text-4xl font-bold mb-4">
          Powerful Features for Self-Discovery
        </h2>
        <p className="text-muted-foreground text-lg">
          Soul Sense combines psychological science with cutting-edge technology to give you a
          clearer picture of your emotional world.
        </p>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="grid md:grid-cols-2 lg:grid-cols-3 gap-8"
      >
        {features.map((feature) => (
          <motion.div
            key={feature.name}
            variants={item}
            className="p-8 rounded-2xl border bg-background hover:shadow-lg hover:border-primary/20 transition-all group"
          >
            <div
              className={`w-12 h-12 rounded-xl ${feature.bg} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}
            >
              <feature.icon className={`h-6 w-6 ${feature.color}`} />
            </div>
            <h3 className="text-xl font-bold mb-3">{feature.name}</h3>
            <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
          </motion.div>
        ))}
      </motion.div>
    </Section>
  );
}
