import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/lib/utils';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { motion } from 'framer-motion';

interface StatsCardProps {
  title: string;
  value: string | number;
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

  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Card
        className={cn(
          'backdrop-blur-xl bg-opacity-60 dark:bg-black/60 border-white/20 hover:border-blue-500/40 transition-all shadow-xl group relative overflow-hidden rounded-2xl',
          className
        )}
      >
        {/* Decorative Background Flare */}
        <div
          className={cn(
            'absolute -right-4 -top-4 w-24 h-24 blur-3xl opacity-10 rounded-full',
            color === 'blue' ? 'bg-blue-500' : color === 'purple' ? 'bg-purple-500' : 'bg-cyan-500'
          )}
        />

        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
          <CardTitle className="text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">
            {title}
          </CardTitle>
          <div
            className={cn(
              'p-2 rounded-xl bg-opacity-10 transition-colors group-hover:bg-opacity-20',
              color === 'blue'
                ? 'bg-blue-500 text-blue-500'
                : color === 'purple'
                  ? 'bg-purple-500 text-purple-500'
                  : 'bg-cyan-500 text-cyan-500'
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="flex items-baseline gap-2">
            <div className="text-3xl font-black tracking-tight text-foreground">{value}</div>
            {trend && (
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/50 px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-700">
                {getTrendIcon()}
                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                  Live
                </span>
              </div>
            )}
          </div>
          {description && (
            <p className="text-xs font-medium text-slate-500 dark:text-slate-500 mt-2 flex items-center gap-1">
              <span className="w-1 h-1 rounded-full bg-blue-500/50" />
              {description}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
