import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui';
import { format, parseISO } from 'date-fns';

export function ActivityAreaChart({ data }: { data: any[] }) {
  // Transform GitHub commit activity (weeks) to chart format
  const chartData = data.map((week) => ({
    date: new Date(week.week * 1000).toISOString().split('T')[0],
    commits: week.total,
  }));

  // Filter data to start strictly from December 15th, 2025
  const START_DATE = '2025-12-15';

  // Also trim trailing zeros to focus strictly on the active period
  const reversedData = [...chartData].reverse();
  const lastActiveIndexFromEnd = reversedData.findIndex((d) => d.commits > 0);
  const lastActiveIndex =
    lastActiveIndexFromEnd !== -1 ? chartData.length - lastActiveIndexFromEnd : chartData.length;

  let focusedData = chartData.slice(0, lastActiveIndex).filter((d) => d.date >= START_DATE);

  // If we only have one data point, pad it with a zero-start to ensure Area rendering
  if (focusedData.length === 1) {
    const firstDate = new Date(focusedData[0].date);
    const prevDate = new Date(firstDate);
    prevDate.setDate(prevDate.getDate() - 7);
    focusedData = [{ date: prevDate.toISOString().split('T')[0], commits: 0 }, ...focusedData];
  }

  return (
    <Card className="h-full backdrop-blur-md lg:backdrop-blur-2xl bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 shadow-sm hover:shadow-md transition-all rounded-3xl overflow-hidden group">
      <CardHeader>
        <CardTitle className="text-lg font-bold text-slate-900 dark:text-white leading-none">
          Engineering Velocity
        </CardTitle>
        <CardDescription className="text-xs text-slate-600 dark:text-slate-400 font-medium mt-1">
          Commit frequency aggregated by week during the project&apos;s active lifespan
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={focusedData}>
              <defs>
                <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.05} vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(str) => format(parseISO(str), 'MMM d')}
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
                fontWeight={500}
              />
              <YAxis
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}`}
                fontWeight={500}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.2)',
                  backdropFilter: 'blur(8px)',
                }}
                itemStyle={{ color: 'hsl(var(--primary))', fontSize: '12px', fontWeight: 'bold' }}
                labelStyle={{
                  color: '#94a3b8',
                  fontSize: '10px',
                  marginBottom: '4px',
                  fontWeight: 'bold',
                  textTransform: 'uppercase',
                }}
              />
              <Area
                type="monotone"
                dataKey="commits"
                stroke="hsl(var(--primary))"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorCommits)"
                animationDuration={2000}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
