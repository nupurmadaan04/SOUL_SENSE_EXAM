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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 col-span-full">
      {/* Top Reviewers */}
      <Card className="backdrop-blur-xl bg-white/95 dark:bg-slate-900/80 border-slate-200/90 dark:border-white/10 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all group">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Award className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
                Top Reviewers
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-medium mt-1">
                Engineers ensuring architectural integrity
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {top_reviewers.length === 0 ? (
              <div className="text-center text-sm text-slate-500 py-8 italic">
                Scanning repository for recent peer reviews...
              </div>
            ) : (
              top_reviewers.map((reviewer, i) => (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  key={reviewer.name}
                  className="flex items-center justify-between group/item p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-all duration-200"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="flex-shrink-0 font-mono text-[10px] font-bold text-slate-400 w-4 text-center">
                      #{i + 1}
                    </div>
                    <Avatar className="h-8 w-8 ring-2 ring-white dark:ring-slate-800 flex-shrink-0">
                      <AvatarImage src={reviewer.avatar} />
                      <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-[10px] font-black">
                        {reviewer.name[0].toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-bold text-slate-800 dark:text-slate-200 group-hover/item:text-purple-600 dark:group-hover/item:text-purple-400 transition-colors truncate">
                        {reviewer.name}
                      </span>
                      {reviewer.is_maintainer && (
                        <span className="text-[8px] font-bold uppercase tracking-wider text-purple-500 leading-none">
                          Maintainer
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400">
                    {reviewer.count} reviews
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Community Happiness */}
      <Card className="backdrop-blur-xl bg-white/95 dark:bg-slate-900/80 border-slate-200/90 dark:border-white/10 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Smile className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
                Community Health
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-medium mt-1">
                Based on {analyzed_comments} recent interactions
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center pt-8 pb-10">
          <div className="relative">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="mb-4 p-4 bg-gradient-to-br from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 rounded-full shadow-lg ring-1 ring-slate-100 dark:ring-white/10"
            >
              {getSentimentIcon(community_happiness)}
            </motion.div>
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-emerald-500 text-white text-[9px] font-bold uppercase tracking-widest rounded-full shadow-sm whitespace-nowrap">
              {getSentimentLabel(community_happiness)}
            </div>
          </div>

          <div className="mt-6 text-4xl font-black text-slate-900 dark:text-white">
            {community_happiness}%
          </div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-6">
            Sentiment Score
          </p>

          {/* Meter Bar */}
          <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden relative">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${community_happiness}%` }}
              className="h-full bg-gradient-to-r from-red-500 via-yellow-400 to-emerald-500 transition-all duration-1000 ease-out"
            />
          </div>
          <div className="flex justify-between w-full text-[9px] font-bold uppercase tracking-widest text-slate-400 mt-2 px-1">
            <span>Critical</span>
            <span>Stable</span>
            <span>Vibrant</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
