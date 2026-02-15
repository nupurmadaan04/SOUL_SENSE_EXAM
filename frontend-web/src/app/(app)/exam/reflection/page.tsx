'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { MessageSquare } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui';
const MAX_CHARACTERS = 500;

const fadeInVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { ease: 'easeOut' },
};

export default function ReflectionPage() {
  const router = useRouter();
  const [reflection, setReflection] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const characterCount = reflection.length;
  const isNearLimit = characterCount >= MAX_CHARACTERS * 0.9;
  const isFull = characterCount >= MAX_CHARACTERS;

  const handleSkip = () => {
    // Navigate to results without saving reflection
    router.push('/results');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setIsSubmitting(true);

      // TODO: Call API endpoint to save reflection
      // const response = await fetch('/api/exam/reflection', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ reflection }),
      // });
      // if (!response.ok) throw new Error('Failed to save reflection');

      // For now, simulate submission delay
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Navigate to results after successful submission
      router.push('/results');
    } catch (error) {
      // TODO: Show error toast notification
      console.error('Failed to save reflection:', error);
      setIsSubmitting(false);
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    if (newText.length <= MAX_CHARACTERS) {
      setReflection(newText);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
      <motion.div
        initial="initial"
        animate="animate"
        variants={fadeInVariants}
        transition={{ delay: 0 }}
        className="mb-8"
      >
        <div className="space-y-2 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            Take a moment to reflect
          </h1>
          <p className="text-lg text-muted-foreground">
            How did you feel during this assessment?
          </p>
        </div>
      </motion.div>

      <motion.form
        initial="initial"
        animate="animate"
        variants={fadeInVariants}
        transition={{ delay: 0.1 }}
        onSubmit={handleSubmit}
      >
        <Card className="border border-border/50 bg-card shadow-sm">
          <CardHeader className="pb-6">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-primary/10 p-3">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-lg">Your Reflection</CardTitle>
                <CardDescription className="mt-1">
                  Optional • This helps us understand your experience. Leave blank if you prefer not to share.
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            <div>
              <textarea
                value={reflection}
                onChange={handleTextChange}
                placeholder="Share your thoughts about the assessment... What was the experience like for you?"
                maxLength={MAX_CHARACTERS}
                disabled={isSubmitting}
                rows={6}
                className={`w-full rounded-md border-2 border-border bg-background p-4 text-sm placeholder:text-muted-foreground/60 transition-colors focus:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:bg-muted disabled:opacity-50 ${
                  isFull ? 'border-amber-500/50' : 'hover:border-border/80'
                }`}
              />

              <div className="mt-3 flex items-center justify-between text-sm">
                <span
                  className={`transition-colors ${
                    isNearLimit ? 'font-medium text-amber-600' : 'text-muted-foreground'
                  }`}
                >
                  {characterCount} / {MAX_CHARACTERS} characters
                </span>
                {characterCount > 0 && (
                  <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      layoutId="progress-bar"
                      initial={{ width: 0 }}
                      animate={{
                        width: `${(characterCount / MAX_CHARACTERS) * 100}%`,
                      }}
                      className={`h-full transition-colors ${
                        isNearLimit ? 'bg-amber-500' : 'bg-primary'
                      }`}
                    />
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <motion.div
          initial="initial"
          animate="animate"
          variants={fadeInVariants}
          transition={{ delay: 0.2 }}
          className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between"
        >
          <Button
            type="button"
            onClick={handleSkip}
            disabled={isSubmitting}
            variant="outline"
            className="h-11 rounded-lg px-6 font-medium"
          >
            Skip
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting}
            className="h-11 rounded-lg px-6 font-medium"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Saving...
              </span>
            ) : (
              'Submit Reflection'
            )}
          </Button>
        </motion.div>

        <motion.p
          initial="initial"
          animate="animate"
          variants={fadeInVariants}
          transition={{ delay: 0.25 }}
          className="mt-6 text-center text-sm text-muted-foreground"
        >
          Your reflection is kept confidential and used only to improve future assessments.
        </motion.p>
      </motion.form>
    </div>
  );
}
