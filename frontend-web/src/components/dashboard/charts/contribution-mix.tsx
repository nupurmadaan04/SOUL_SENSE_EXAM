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
            color: '#3B82F6',
            description: 'Functional code commits',
          },
          { name: 'Docs', value: 25, color: '#10B981', description: 'README & Wiki updates' },
          { name: 'Triage', value: 20, color: '#F59E0B', description: 'Issues & Support' },
          { name: 'Reviews', value: 10, color: '#8B5CF6', description: 'Code Quality checks' },
        ];

  return (
    <Card className="col-span-full md:col-span-1 lg:col-span-3 backdrop-blur-xl bg-opacity-60 dark:bg-black/60 border-white/20 shadow-xl rounded-2xl overflow-hidden relative group">
      <CardHeader className="pb-0 flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-xl font-bold">Project Persona</CardTitle>
          <CardDescription>Weighted impact by contribution type</CardDescription>
        </div>
        <div className="p-2 rounded-full hover:bg-slate-800 transition-colors cursor-help group/info relative">
          <Info className="h-4 w-4 text-slate-500" />
          <div className="absolute right-0 top-10 w-64 p-3 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl opacity-0 group-hover/info:opacity-100 transition-opacity z-50 pointer-events-none">
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-2">
              Metric Methodology
            </p>
            <p className="text-xs text-slate-300 leading-relaxed">
              This breakdown evaluates the **volume of events** (commits, PR comments, issue
              actions) normalized across different repository domains to show where the community is
              focusing its energy.
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
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '12px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  }}
                  itemStyle={{
                    color: '#e2e8f0',
                    fontSize: '10px',
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
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">
                Total Events
              </span>
            </div>
          </div>

          {/* Custom Descriptive Legend */}
          <div className="w-full xl:w-1/2 grid grid-cols-1 gap-3 py-4">
            {chartData.map((item, i) => (
              <div
                key={i}
                className="flex flex-col gap-0.5 group/item border-l-2 border-transparent hover:border-slate-700 dark:hover:border-slate-400 pl-3 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full shadow-sm"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-[11px] font-black uppercase tracking-tight text-slate-900 dark:text-slate-100">
                      {item.name}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-xs font-mono font-black text-blue-600 dark:text-blue-400">
                      {item.value}%
                    </span>
                    <span className="text-[9px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tighter">
                      {item.count} {item.unit}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] font-medium text-slate-500 group-hover/item:text-slate-800 dark:group-hover/item:text-slate-300 transition-colors">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Methodology Info */}
        <div className="mt-4 pt-4 border-t border-slate-200/5 flex items-center justify-between text-[9px] font-bold text-slate-500 uppercase tracking-widest px-2">
          <span>Basis: Event Volume</span>
          <span className="text-blue-500/50">Normalized Scale</span>
        </div>
      </CardContent>
    </Card>
  );
}
