import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui';
import { Info } from 'lucide-react';

export function ContributionMixChart({ data }: { data: any[] }) {
  // Use backend data or fallback
  const chartData =
    data && data.length > 0
      ? data
      : [
          {
            name: 'Core Logic',
            value: 45,
            color: 'hsl(var(--primary))',
            description: 'Functional code commits',
          },
          {
            name: 'Docs',
            value: 25,
            color: 'hsl(var(--secondary))',
            description: 'README & Wiki updates',
          },
          { name: 'Triage', value: 20, color: '#3b82f6', description: 'Issues & Support' },
          { name: 'Reviews', value: 10, color: '#8b5cf6', description: 'Code Quality checks' },
        ];

  return (
    <Card className="col-span-full md:col-span-1 lg:col-span-3 backdrop-blur-md lg:backdrop-blur-2xl bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-white/10 shadow-sm hover:shadow-md transition-all rounded-3xl overflow-hidden relative group">
      <CardHeader className="pb-0 flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-lg font-bold text-slate-900 dark:text-white leading-none">
            Project Persona
          </CardTitle>
          <CardDescription className="text-xs text-slate-600 dark:text-slate-400 font-medium mt-1">
            Weighted impact by contribution type
          </CardDescription>
        </div>
        <div className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-help group/info relative">
          <Info className="h-4 w-4 text-slate-400" />
          <div className="absolute right-0 top-10 w-64 p-4 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl opacity-0 group-hover/info:opacity-100 transition-opacity z-50 pointer-events-none backdrop-blur-md">
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-2">
              Metric Methodology
            </p>
            <p className="text-xs text-slate-300 leading-relaxed font-medium">
              This breakdown evaluates the **volume of events** (commits, PR comments, issue
              actions) normalized across different repository domains.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 pb-2">
        <div className="flex flex-col xl:flex-row items-center gap-6">
          <div className="h-[200px] w-full xl:w-1/2 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                  stroke="none"
                  animationBegin={500}
                  animationDuration={1500}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      className="hover:opacity-80 transition-opacity cursor-pointer"
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '12px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.2)',
                    backdropFilter: 'blur(8px)',
                  }}
                  itemStyle={{
                    color: '#e2e8f0',
                    fontSize: '11px',
                    fontWeight: 'bold',
                    textTransform: 'uppercase',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Centered Total Label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-3xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                {(() => {
                  const total = chartData.reduce((acc, curr) => acc + (curr.count || 0), 0);
                  if (total >= 1000) return `${(total / 1000).toFixed(1)}k`;
                  return total > 0 ? total : '100%';
                })()}
              </span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">
                Total Events
              </span>
            </div>
          </div>

          {/* Custom Descriptive Legend */}
          <div className="w-full xl:w-1/2 grid grid-cols-1 gap-3 py-4">
            {chartData.map((item, i) => (
              <div
                key={i}
                className="flex flex-col gap-0.5 group/item border-l-2 border-transparent hover:border-slate-200 dark:hover:border-slate-700 pl-3 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full shadow-sm ring-1 ring-white/10"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-[11px] font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">
                      {item.name}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-xs font-mono font-bold text-blue-600 dark:text-blue-400">
                      {item.value}%
                    </span>
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-tighter">
                      {item.count} {item.unit}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] font-medium text-slate-500 group-hover/item:text-slate-700 dark:group-hover/item:text-slate-400 transition-colors line-clamp-1">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Methodology Info */}
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between text-[9px] font-bold text-slate-400 uppercase tracking-widest px-1">
          <span>Basis: Event Volume</span>
          <span className="text-blue-500/80">Normalized Scale</span>
        </div>
      </CardContent>
    </Card>
  );
}
