'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useFetchDashboardData } from '@/hooks/useDashboard';
import { ChevronDown, BarChart3 } from 'lucide-react';

interface FilterDropdownProps {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}

function FilterDropdown({ label, value, options, onChange }: FilterDropdownProps) {
  return (
    <div className="flex flex-col space-y-0.5 min-w-0 w-full">
      <label className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider truncate">{label}</label>
      <div className="relative w-full min-w-0">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ WebkitAppearance: 'none', MozAppearance: 'none', appearance: 'none', backgroundImage: 'none' }}
          className="w-full pl-2 pr-5 py-1 bg-background text-foreground border border-border/80 rounded-xl shadow-xs focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-[11px] font-semibold cursor-pointer truncate transition-all hover:border-primary/40"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} className="bg-popover text-popover-foreground py-1">
              {option.label}
            </option>
          ))}
        </select>
        <div className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
          <ChevronDown className="h-3 w-3" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardCharts() {
  const searchParams = useSearchParams();
  const { replace } = useRouter();
  const pathname = usePathname();
  const [isHydrated, setIsHydrated] = useState(false);

  const { data, loading, error } = useFetchDashboardData();

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const handleFilterChange = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    replace(`${pathname}?${params.toString()}`);
  };

  const timeframe = searchParams.get('timeframe') || '30d';
  const examType = searchParams.get('exam_type') || '';
  const sentiment = searchParams.get('sentiment') || '';

  const timeframeOptions = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
  ];

  const examTypeOptions = [
    { value: '', label: 'All Types' },
    { value: 'standard', label: 'Standard' },
    { value: 'advanced', label: 'Advanced' },
  ];

  const sentimentOptions = [
    { value: '', label: 'All' },
    { value: 'positive', label: 'Positive' },
    { value: 'neutral', label: 'Neutral' },
    { value: 'negative', label: 'Negative' },
  ];

  const chartData = data?.trend_points?.map((point) => ({
    date: new Date(point.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    score: point.score,
    sentiment: point.sentiment_score,
  })) || [];

  if (!isHydrated) {
    return (
      <div className="border border-border/80 bg-card/90 backdrop-blur-md p-5 rounded-3xl shadow-xl h-full overflow-hidden">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-muted/40 rounded w-1/3 mb-2"></div>
          <div className="h-32 bg-muted/30 rounded-2xl"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-border/80 bg-card/90 backdrop-blur-md p-5 rounded-3xl shadow-xl flex flex-col justify-between h-full overflow-hidden">
      <div className="min-w-0 w-full">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/40">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1.5 rounded-xl bg-primary/10 text-primary shrink-0">
              <BarChart3 className="h-4 w-4" />
            </div>
            <h3 className="text-xs font-bold text-foreground uppercase tracking-wider truncate">Emotional Trend</h3>
          </div>
          <span className="text-[10px] font-semibold text-muted-foreground shrink-0">Score Index</span>
        </div>

        <div className="grid grid-cols-3 gap-1.5 mb-2 w-full min-w-0">
          <FilterDropdown
            label="Range"
            value={timeframe}
            options={timeframeOptions}
            onChange={(value) => handleFilterChange('timeframe', value)}
          />
          <FilterDropdown
            label="Type"
            value={examType}
            options={examTypeOptions}
            onChange={(value) => handleFilterChange('exam_type', value)}
          />
          <FilterDropdown
            label="Sentiment"
            value={sentiment}
            options={sentimentOptions}
            onChange={(value) => handleFilterChange('sentiment', value)}
          />
        </div>
      </div>

      <div className="h-32 w-full mt-auto">
        {loading ? (
          <div className="h-full w-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
          </div>
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
              <XAxis dataKey="date" stroke="currentColor" className="text-muted-foreground opacity-50 text-[9px]" tickLine={false} />
              <YAxis stroke="currentColor" className="text-muted-foreground opacity-50 text-[9px]" domain={[0, 100]} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--popover)',
                  borderColor: 'var(--border)',
                  borderRadius: '0.75rem',
                  fontSize: '0.75rem',
                }}
              />
              <Line type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 3, fill: 'hsl(var(--primary))' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full w-full flex flex-col items-center justify-center text-center p-2 rounded-2xl bg-muted/20 border border-border/40">
            <p className="text-[11px] font-semibold text-muted-foreground">No trend data available</p>
            <p className="text-[9px] text-muted-foreground/70 mt-0.5">Complete assessments to see your emotional trajectory</p>
          </div>
        )}
      </div>
    </div>
  );
}