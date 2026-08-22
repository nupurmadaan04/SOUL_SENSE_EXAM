import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/lib/utils';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { motion } from 'framer-motion';

interface StatsCardProps {
  title: string;
  value: string | number | any;
  description?: string;
  icon: LucideIcon;
  className?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

export function StatsCard({
  title,
  value,
  description,
  icon: Icon,
  className,
  trend,
  color = 'blue',
}: StatsCardProps) {
  const formatValue = (val: any): string | number => {
    if (val === null || val === undefined) return 0;
    if (typeof val === 'number' || typeof val === 'string') return val;
    if (typeof val === 'object') {
      if ('total' in val && (typeof val.total === 'number' || typeof val.total === 'string')) {
        return val.total;
      }
      if ('count' in val && (typeof val.count === 'number' || typeof val.count === 'string')) {
        return val.count;
      }
      if ('stars' in val && (typeof val.stars === 'number' || typeof val.stars === 'string')) {
        return val.stars;
      }
      if (Array.isArray(val)) return val.length;
      return Object.keys(val).length;
    }
    return String(val);
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3 w-3 text-emerald-500" />;
      case 'down':
        return <TrendingDown className="h-3 w-3 text-rose-500" />;
      default:
        return <Minus className="h-3 w-3 text-slate-500" />;
    }
  };

  const getThemeStyles = () => {
    switch (color) {
      case 'purple':
        return {
          bg: 'bg-purple-500/10',
          text: 'text-purple-600 dark:text-purple-400',
          border: 'group-hover:border-purple-500/30',
        };
      case 'cyan':
        return {
          bg: 'bg-cyan-500/10',
          text: 'text-cyan-600 dark:text-cyan-400',
          border: 'group-hover:border-cyan-500/30',
        };
      default:
        return {
          bg: 'bg-blue-500/10',
          text: 'text-blue-600 dark:text-blue-400',
          border: 'group-hover:border-blue-500/30',
        };
    }
  };

  const theme = getThemeStyles();

  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Card
        className={cn(
          'backdrop-blur-xl bg-white/95 dark:bg-slate-900/80 border-slate-200/90 dark:border-white/10 transition-all shadow-sm hover:shadow-md group relative overflow-hidden rounded-2xl',
          theme.border,
          className
        )}
      >
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
          <CardTitle className="text-xs font-bold tracking-wider text-slate-600 dark:text-slate-400 uppercase">
            {title}
          </CardTitle>
          <div
            className={cn(
              'p-2 rounded-xl transition-colors group-hover:bg-opacity-80',
              theme.bg,
              theme.text
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="flex items-baseline gap-2">
            <div className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">
              {formatValue(value)}
            </div>
            {trend && (
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-white/5 px-2 py-0.5 rounded-full border border-slate-200 dark:border-white/5">
                {getTrendIcon()}
              </div>
            )}
          </div>
          {description && (
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mt-2 flex items-center gap-1">
              {description}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
