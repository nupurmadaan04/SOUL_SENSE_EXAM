import { Skeleton } from '@/components/ui';

export function DashboardSkeleton() {
  return (
    <div className="flex flex-col space-y-12 animate-pulse pb-10">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-3xl bg-slate-200 dark:bg-slate-800/50" />
        ))}
      </div>
      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="col-span-full h-[350px] rounded-3xl bg-slate-200 dark:bg-slate-800/50" />
        <Skeleton className="col-span-full lg:col-span-3 h-[300px] rounded-3xl bg-slate-200 dark:bg-slate-800/50" />
        <Skeleton className="col-span-full lg:col-span-1 h-[300px] rounded-3xl bg-slate-200 dark:bg-slate-800/50" />
        <Skeleton className="col-span-full h-[300px] rounded-3xl bg-slate-200 dark:bg-slate-800/50" />
      </div>
    </div>
  );
}
