import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui';
import { Smile, Frown, Meh, Award } from 'lucide-react';
import { motion } from 'framer-motion';

interface Reviewer {
  name: string;
  avatar: string;
  count: number;
  is_maintainer?: boolean;
}

interface ReviewerMetricsProps {
  data: {
    top_reviewers: Reviewer[];
    community_happiness: number; // 0-100
    analyzed_comments: number;
  };
}

export function ReviewerMetrics({ data }: ReviewerMetricsProps) {
  const { top_reviewers, community_happiness, analyzed_comments } = data || {
    top_reviewers: [],
    community_happiness: 50,
    analyzed_comments: 0,
  };

  const getSentimentIcon = (score: number) => {
    if (score >= 70) return <Smile className="h-8 w-8 text-green-500" />;
    if (score >= 40) return <Meh className="h-8 w-8 text-yellow-500" />;
    return <Frown className="h-8 w-8 text-red-500" />;
  };

  const getSentimentLabel = (score: number) => {
    if (score >= 80) return 'Thriving';
    if (score >= 60) return 'Healthy';
    if (score >= 40) return 'Neutral';
    if (score >= 20) return 'Tense';
    return 'Toxic'; // Ideally shouldn't happen
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 col-span-full">
      {/* Top Reviewers */}
      <Card className="backdrop-blur-md bg-opacity-50 dark:bg-black/40 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="h-5 w-5 text-purple-500" />
            Top Reviewers
          </CardTitle>
          <CardDescription>Heroes who ensure code quality</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {top_reviewers.length === 0 ? (
              <div className="text-center text-sm text-slate-500 py-4">
                No reviews found recently.
              </div>
            ) : (
              top_reviewers.map((reviewer, i) => (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  key={reviewer.name}
                  className="flex items-center justify-between group/item p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="font-mono text-sm text-slate-400 w-4">#{i + 1}</div>
                    <Avatar className="h-8 w-8 ring-2 ring-transparent group-hover/item:ring-blue-500/30 transition-all">
                      <AvatarImage src={reviewer.avatar} />
                      <AvatarFallback>{reviewer.name[0]}</AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                      <span className="text-sm font-bold tracking-tight">{reviewer.name}</span>
                      {reviewer.is_maintainer && (
                        <span className="text-[8px] font-black uppercase tracking-widest text-purple-500 leading-none mt-0.5">
                          Maintainer
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-xs font-black px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 group-hover/item:text-blue-500 transition-colors">
                    {reviewer.count} REVIEWS
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Community Happiness */}
      <Card className="backdrop-blur-md bg-opacity-50 dark:bg-black/40 border-white/10">
        <CardHeader>
          <CardTitle>Community Happiness</CardTitle>
          <CardDescription>Based on {analyzed_comments} recent PR comments</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center pt-4 pb-8">
          <div className="mb-4">{getSentimentIcon(community_happiness)}</div>
          <div className="text-3xl font-extrabold mb-1">{community_happiness}%</div>
          <div className="text-sm font-medium text-slate-400 mb-6">
            {getSentimentLabel(community_happiness)}
          </div>

          {/* Meter Bar */}
          <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden relative">
            <div
              className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all duration-1000 ease-out"
              style={{ width: `${community_happiness}%` }}
            />
          </div>
          <div className="flex justify-between w-full text-xs text-slate-600 mt-2 px-1">
            <span>Critical</span>
            <span>Neutral</span>
            <span>Vibrant</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
