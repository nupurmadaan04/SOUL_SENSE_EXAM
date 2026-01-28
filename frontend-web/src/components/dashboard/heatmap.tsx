import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui';
import { cn } from '@/lib/utils';

export function ContributionHeatmap() {
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  const dayLabels = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

  // Generate data organized by weeks (52 columns x 7 rows)
  const generateData = () => {
    const weeks = [];
    const today = new Date();
    // Start from the most recent Sunday
    const startDate = new Date(today);
    startDate.setDate(today.getDate() - today.getDay() - 51 * 7);

    for (let w = 0; w < 52; w++) {
      const days = [];
      for (let d = 0; d < 7; d++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + w * 7 + d);
        days.push({
          date: date.toISOString().split('T')[0],
          month: months[date.getMonth()],
          dayOfWeek: d,
          // Generate slightly more patterned data
          count: Math.random() > 0.7 ? Math.floor(Math.random() * 8) : Math.random() > 0.9 ? 2 : 0,
        });
      }
      weeks.push(days);
    }
    return weeks;
  };

  const weeks = generateData();

  const getColor = (count: number) => {
    if (count === 0) return 'bg-slate-100 dark:bg-slate-900';
    if (count <= 2) return 'bg-blue-300 dark:bg-blue-900/60';
    if (count <= 4) return 'bg-blue-500 dark:bg-blue-700';
    if (count <= 6) return 'bg-blue-600 dark:bg-blue-500';
    return 'bg-purple-500 dark:bg-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.4)]';
  };

  return (
    <Card className="col-span-full lg:col-span-4 backdrop-blur-xl bg-opacity-60 dark:bg-black/60 border-white/20 shadow-xl overflow-hidden rounded-2xl group">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-xl font-bold">Project Pulse</CardTitle>
          <CardDescription>Engineering activity frequency over the last 52 weeks</CardDescription>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-tighter">
          <span>Quiet</span>
          <div className="flex gap-1">
            <div className="w-2.5 h-2.5 rounded-sm bg-slate-900" />
            <div className="w-2.5 h-2.5 rounded-sm bg-blue-900" />
            <div className="w-2.5 h-2.5 rounded-sm bg-blue-600" />
            <div className="w-2.5 h-2.5 rounded-sm bg-purple-500" />
          </div>
          <span>Active</span>
        </div>
      </CardHeader>
      <CardContent className="pb-8 pt-2 overflow-x-auto">
        <div className="flex gap-3 min-w-[700px] justify-center lg:justify-start">
          {/* Day Labels */}
          <div className="flex flex-col gap-[3px] pr-2 pt-1 text-[9px] font-bold text-slate-500 uppercase">
            {dayLabels.map((label, i) => (
              <div key={i} className="h-[11px] md:h-[13px] flex items-center">
                {label}
              </div>
            ))}
          </div>

          <div className="flex-1 space-y-1">
            {/* Months Row */}
            <div className="flex gap-[3px] h-4 mb-1">
              {weeks.map((week, i) => {
                const firstDay = week[0];
                const showMonth = i === 0 || (i > 0 && weeks[i - 1][0].month !== firstDay.month);
                return (
                  <div
                    key={i}
                    className="w-[11px] md:w-[13px] text-[9px] font-bold text-slate-500 uppercase"
                  >
                    {showMonth ? firstDay.month : ''}
                  </div>
                );
              })}
            </div>

            {/* Grid */}
            <div className="flex gap-[3px]">
              {weeks.map((week, weekIndex) => (
                <div key={weekIndex} className="flex flex-col gap-[3px]">
                  {week.map((day, dayIndex) => (
                    <TooltipProvider key={`${weekIndex}-${dayIndex}`}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div
                            className={cn(
                              'w-[11px] h-[11px] md:w-[13px] md:h-[13px] rounded-[2px] cursor-crosshair transition-all duration-300',
                              getColor(day.count),
                              'hover:scale-150 hover:z-50 hover:shadow-lg'
                            )}
                          />
                        </TooltipTrigger>
                        <TooltipContent className="bg-slate-900 border-slate-700 text-slate-100 px-3 py-1.5 rounded-lg shadow-2xl">
                          <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-0.5">
                            {day.date}
                          </p>
                          <p className="text-xs font-medium">
                            {day.count === 0 ? 'No' : day.count}{' '}
                            {day.count === 1 ? 'contribution' : 'contributions'}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
