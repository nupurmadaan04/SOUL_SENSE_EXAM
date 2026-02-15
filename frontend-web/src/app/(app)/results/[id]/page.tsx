'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useResults } from '@/hooks/useResults';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScoreGauge, CategoryBreakdown, RecommendationCard } from '@/components/results';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Download, RefreshCw, Calendar, Clock } from 'lucide-react';

export default function ResultDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = params?.id as string | string[] | undefined;
  const examId = rawId
    ? parseInt(Array.isArray(rawId) ? rawId[0] : rawId, 10)
    : NaN;

  if (!examId || Number.isNaN(examId)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Invalid result</CardTitle>
            <CardDescription>
              The requested result ID is invalid. Please check the link and try again.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/results')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to results
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  const { result, isLoading, error } = useResults(examId);

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format duration
  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Handle retake
  const handleRetake = () => {
    router.push('/exam');
  };

  // Handle export (placeholder)
  const handleExport = () => {
    window.print();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <Skeleton className="h-8 w-64" />
        </div>
        <Skeleton className="h-[400px] w-full" />
        <Skeleton className="h-[300px] w-full" />
      </div>
    );
  }

  // Error state
  if (error || !result) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card className="border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950">
          <CardHeader>
            <CardTitle className="text-red-900 dark:text-red-100">Error Loading Results</CardTitle>
            <CardDescription className="text-red-700 dark:text-red-300">
              {error || 'Unable to load exam results. Please try again.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/results')}>
              View All Results
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Transform categories data for CategoryBreakdown component
  const categoryScores = result.categories.map(cat => {
    const maxScore = typeof cat.max_score === 'number' && cat.max_score > 0 ? cat.max_score : null;
    const scorePercentage = maxScore ? (cat.score / maxScore) * 100 : 0;
    return {
      name: cat.name,
      score: scorePercentage,
    };
  });

  return (
    <div className="space-y-8 pb-12">
      {/* Header with Back Button */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Results
        </Button>
        
        <div className="flex gap-2 no-print">
          <Button variant="outline" onClick={handleRetake}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retake Exam
          </Button>
          <Button variant="default" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export PDF
          </Button>
        </div>
      </div>

      {/* Page Title & Metadata */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">Exam Results</h1>
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            <span>
              {result.completed_at || result.timestamp
                ? formatDate(result.completed_at || result.timestamp)
                : 'N/A'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span>{formatDuration(result.duration_seconds)}</span>
          </div>
        </div>
      </div>

      {/* Overall Score Section */}
      <Card className="overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
          <CardTitle>Overall Performance</CardTitle>
          <CardDescription>Your comprehensive emotional intelligence score</CardDescription>
        </CardHeader>
        <CardContent className="pt-8 pb-8 flex justify-center">
          <ScoreGauge 
            score={result.overall_score || result.total_score || 0} 
            size="lg"
            label="Overall Score"
            animated
          />
        </CardContent>
      </Card>

      {/* Category Breakdown */}
      {result.categories && result.categories.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
            <CardDescription>
              Detailed performance across emotional intelligence dimensions
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <CategoryBreakdown 
              categories={categoryScores}
              showLabels
              animated
            />
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {result.recommendations && result.recommendations.length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Personalized Recommendations</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Tailored suggestions to improve your emotional intelligence
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {result.recommendations.map((recommendation, index) => (
              <RecommendationCard 
                key={`${recommendation.id}-${index}`} 
                recommendation={recommendation}
              />
            ))}
          </div>
        </div>
      )}

      {/* Reflection Section */}
      {result.reflection && (
        <Card>
          <CardHeader>
            <CardTitle>Your Reflection</CardTitle>
            <CardDescription>Personal notes from your assessment</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose dark:prose-invert max-w-none">
              <p className="whitespace-pre-wrap">{result.reflection}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons (Mobile-friendly, bottom) */}
      <div className="flex flex-col sm:flex-row gap-3 no-print pt-4 border-t">
        <Button 
          variant="outline" 
          onClick={handleRetake}
          className="flex-1"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retake Exam
        </Button>
        <Button 
          variant="default"
          onClick={handleExport}
          className="flex-1"
        >
          <Download className="mr-2 h-4 w-4" />
          Export as PDF
        </Button>
      </div>

      {/* Print Styles */}
      <style jsx global>{`
        @media print {
          .no-print {
            display: none !important;
          }
          
          body {
            print-color-adjust: exact;
            -webkit-print-color-adjust: exact;
          }
          
          @page {
            margin: 1cm;
          }
        }
      `}</style>
    </div>
  );
}
