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
    <Card className="h-full backdrop-blur-xl bg-white/60 dark:bg-slate-900/60 border-white/20 shadow-xl rounded-2xl overflow-hidden">
      <CardHeader>
        <CardTitle className="text-xl font-bold">Engineering Velocity</CardTitle>
        <CardDescription>
          Commit frequency aggregated by week during the project&apos;s active lifespan
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={focusedData}>
              <defs>
                <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.05} vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(str) => format(parseISO(str), 'MMM d')}
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '12px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                }}
                itemStyle={{ color: '#3B82F6', fontSize: '12px', fontWeight: 'bold' }}
                labelStyle={{ color: '#64748b', fontSize: '10px', marginBottom: '4px' }}
              />
              <Area
                type="monotone"
                dataKey="commits"
                stroke="#3B82F6"
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
