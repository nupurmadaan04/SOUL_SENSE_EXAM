'use client';

import { motion } from 'framer-motion';
import { Star, Quote } from 'lucide-react';
import { Section } from '@/components/layout';
import Image from 'next/image';

const testimonials = [
  {
    content:
      'Soul Sense changed my perspective on leadership. Understanding my EQ helped me connect with my team on a whole new level.',
    author: 'Sarah Jenkins',
    role: 'Tech Lead at InnovateX',
    image: 'https://i.pravatar.cc/150?u=sarah',
  },
  {
    content:
      "The insights I gained from the test were spot-on. It's the first time I felt like an AI actually 'understood' my emotions.",
    author: 'Michael Chen',
    role: 'Marketing Director',
    image: 'https://i.pravatar.cc/150?u=michael',
  },
  {
    content:
      'A must-have for anyone on a self-improvement journey. Simple to use but incredibly deep in its analysis.',
    author: 'Emily Rodriguez',
    role: 'Freelance Designer',
    image: 'https://i.pravatar.cc/150?u=emily',
  },
];

export function Testimonials() {
  return (
    <Section id="testimonials">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h2 className="text-3xl lg:text-4xl font-bold mb-4">Trusted by Minds Everywhere</h2>
        <p className="text-muted-foreground text-lg">
          Join thousands of users who are using Soul Sense to unlock their emotional intelligence.
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {testimonials.map((testimonial, index) => (
          <motion.div
            key={testimonial.author}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
            className="p-8 rounded-2xl border bg-background relative"
          >
            <div className="absolute top-6 right-8 text-primary/10">
              <Quote className="h-12 w-12" />
            </div>
            <div className="flex gap-1 mb-6">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-primary text-primary" />
              ))}
            </div>
            <p className="text-lg text-foreground/90 italic mb-8 relative z-10">
              &quot;{testimonial.content}&quot;
            </p>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full overflow-hidden bg-accent relative">
                <Image
                  src={testimonial.image}
                  alt={testimonial.author}
                  fill
                  className="object-cover"
                  placeholder="blur"
                  blurDataURL="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                />
              </div>
              <div>
                <p className="font-bold">{testimonial.author}</p>
                <p className="text-sm text-muted-foreground">{testimonial.role}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
