'use client';

import React, { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useResults } from '@/hooks/useResults';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Skeleton,
} from '@/components/ui';
import { ScoreGauge, CategoryBreakdown, RecommendationCard } from '@/components/results';
import { ArrowLeft, Download, RefreshCw, Calendar, Clock, Loader2, FileX2 } from 'lucide-react';
import { CategoryBreakdown, RecommendationCard } from '@/components/results';
import { ScoreGauge } from '@/lib/dynamic-imports';
import { ArrowLeft, Download, RefreshCw, Calendar, Clock, Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/toast';
import { apiClient } from '@/lib/api/client';

export default function ResultDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [isDownloading, setIsDownloading] = React.useState(false);
  const rawId = params?.id as string | string[] | undefined;
  const examId = rawId ? parseInt(Array.isArray(rawId) ? rawId[0] : rawId, 10) : NaN;

  const { detailedResult: result, loading: isLoading, error, notFound, fetchDetailedResult } = useResults();

  useEffect(() => {
    if (examId && !Number.isNaN(examId)) {
      // Catch to prevent unhandled rejection — error state is managed by the hook
      fetchDetailedResult(examId).catch(() => { });
    }
  }, [examId, fetchDetailedResult]);

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

  // Handle export with robust binary transport
  const handleExport = async () => {
    try {
      setIsDownloading(true);

      // Explicitly require 'blob' translation from fetch/apiClient
      const response = await apiClient.get<Blob>('/reports/export/pdf', {
        responseType: 'blob',
      });

      // Synthesize the Blob into a temporary geometric URL
      const blob = new Blob([response], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Read explicit filename boundary or manufacture one generically
      const contentDate = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `SoulSense_Report_${contentDate}.pdf`);

      // Mount, trigger physical browser payload, wipe clean
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({
        type: 'success',
        message: 'Report downloaded successfully.',
      });
    } catch (error) {
      console.error('PDF Export Error:', error);
      toast({
        type: 'error',
        message: 'Critically failed to initialize API PDF extraction.',
      });
    } finally {
      setIsDownloading(false);
    }
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

  // Not‑found state (404 / deleted result)
  if (notFound) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.push('/results')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Results
        </Button>
        <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
          <CardHeader className="flex flex-row items-start gap-4">
            <FileX2 className="mt-1 h-8 w-8 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <CardTitle className="text-amber-900 dark:text-amber-100">No Result Found</CardTitle>
              <CardDescription className="text-amber-700 dark:text-amber-300">
                The assessment result you are looking for does not exist or may have been removed.
                Please check the link or go back to view all your results.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/results')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              View All Results
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Generic error state (network failure, server error, etc.)
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
          <CardContent className="flex gap-3">
            <Button variant="outline" onClick={() => fetchDetailedResult(examId).catch(() => { })}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
            <Button onClick={() => router.push('/results')}>View All Results</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Transform categories data for CategoryBreakdown component (null‑safe)
  const categoryScores = (result.category_breakdown ?? []).map((cat) => {
    return {
      name: cat.category_name ?? 'Unknown',
      score: cat.percentage ?? 0,
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
          <Button variant="default" onClick={handleExport} disabled={isDownloading}>
            {isDownloading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {isDownloading ? 'Generating...' : 'Export PDF'}
          </Button>
        </div>
      </div>

      {/* Page Title & Metadata */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">Exam Results</h1>
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            <span>{result.timestamp ? formatDate(result.timestamp) : 'N/A'}</span>
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
            score={result.overall_percentage ?? result.total_score ?? 0}
            size="lg"
            label="Overall Score"
            animated
          />
        </CardContent>
      </Card>

      {/* Category Breakdown */}
      {result.category_breakdown && result.category_breakdown.length > 0 && categoryScores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
            <CardDescription>
              Detailed performance across emotional intelligence dimensions
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <CategoryBreakdown categories={categoryScores} showLabels animated />
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {Array.isArray(result.recommendations) && result.recommendations.length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Personalized Recommendations</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Tailored suggestions to improve your emotional intelligence
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {result.recommendations.map((recommendation, index) => (
              <RecommendationCard key={`rec-${index}`} recommendation={recommendation} />
            ))}
          </div>
        </div>
      )}

      {/* Reflection Section */}
      {(result as any).reflection && (
        <Card>
          <CardHeader>
            <CardTitle>Your Reflection</CardTitle>
            <CardDescription>Personal notes from your assessment</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose dark:prose-invert max-w-none">
              <p className="whitespace-pre-wrap">{(result as any).reflection}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons (Mobile-friendly, bottom) */}
      <div className="flex flex-col sm:flex-row gap-3 no-print pt-4 border-t">
        <Button variant="outline" onClick={handleRetake} className="flex-1">
          <RefreshCw className="mr-2 h-4 w-4" />
          Retake Exam
        </Button>
        <Button
          variant="default"
          onClick={handleExport}
          className="flex-1"
          disabled={isDownloading}
        >
          {isDownloading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          {isDownloading ? 'Generating Report...' : 'Export as PDF'}
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
