'use client';

import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui';
import { FolderTree, Info, Flame } from 'lucide-react';

interface SunburstData {
  name: string;
  value?: number;
  children?: SunburstData[];
}

export function RepositorySunburst({ data }: { data: SunburstData[] }) {
  // Flatten data for nested Pies
  const flattenedData = useMemo(() => {
    if (!data) return { level1: [], level2: [] };

    const level1: any[] = [];
    const level2: any[] = [];

    // Theme-aligned palette: Blue, Indigo, Purple, Pink
    const colors = ['#3B82F6', '#6366F1', '#8B5CF6', '#EC4899'];

    data.forEach((child, i) => {
      const color = colors[i % colors.length];

      // Level 1 Nodes
      const l1Value = child.children
        ? child.children.reduce((acc, c) => acc + (c.value || 0), 0)
        : child.value || 0;

      level1.push({
        name: child.name,
        value: l1Value,
        color: color,
        opacity: 0.8,
      });

      // Level 2 Nodes
      if (child.children) {
        child.children.forEach((grandchild) => {
          level2.push({
            name: `${child.name}/${grandchild.name}`,
            value: grandchild.value || 0,
            color: color,
            opacity: 0.4,
          });
        });
      }
    });

    return { level1, level2 };
  }, [data]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-2 rounded-lg shadow-xl backdrop-blur-md">
          <p className="text-[10px] font-black uppercase text-blue-400 mb-1">{data.name}</p>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">{data.value}</span>
            <span className="text-[10px] text-slate-400">ACTIVITIES</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="col-span-full lg:col-span-2 bg-white border-slate-200 shadow-xl rounded-3xl overflow-hidden group">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-black tracking-tighter flex items-center gap-2 text-slate-900">
          <FolderTree className="h-4 w-4 text-indigo-600" />
          DIRECTORY_HEATMAP
        </CardTitle>
        <CardDescription className="text-xs font-medium text-slate-500">
          Hierarchy of repository attention
        </CardDescription>
      </CardHeader>

      <div className="px-6 py-2 border-y border-slate-100 bg-indigo-50/50">
        <p className="text-[10px] leading-relaxed text-slate-600 font-medium italic">
          <span className="text-indigo-600 font-bold uppercase tracking-tighter mr-2">
            Core Insight:
          </span>
          Visualizes **where the energy is going**. Inner rings are root folders; outer rings are
          sub-folders. Large arcs represent areas of heavy development.
        </p>
      </div>

      <CardContent className="h-[300px] p-0 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            {/* Level 1: Root Directories */}
            <Pie
              data={flattenedData.level1}
              dataKey="value"
              innerRadius={40}
              outerRadius={70}
              paddingAngle={2}
              stroke="none"
              animationDuration={1500}
            >
              {flattenedData.level1.map((entry, index) => (
                <Cell
                  key={`cell-l1-${index}`}
                  fill={entry.color}
                  fillOpacity={entry.opacity}
                  className="hover:fill-opacity-100 transition-all cursor-crosshair"
                />
              ))}
            </Pie>

            {/* Level 2: Sub-folders */}
            <Pie
              data={flattenedData.level2}
              dataKey="value"
              innerRadius={75}
              outerRadius={100}
              paddingAngle={1}
              stroke="none"
              animationDuration={2000}
            >
              {flattenedData.level2.map((entry, index) => (
                <Cell
                  key={`cell-l2-${index}`}
                  fill={entry.color}
                  fillOpacity={entry.opacity}
                  className="hover:fill-opacity-100 transition-all cursor-crosshair"
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center pointer-events-none">
          <Flame className="h-5 w-5 text-orange-500 animate-pulse" />
        </div>

        {/* Legend Overlay */}
        <div className="absolute top-4 right-4 group/info relative">
          <Info className="h-4 w-4 text-slate-300 hover:text-indigo-400 cursor-help transition-colors" />
          <div className="absolute top-6 right-0 w-48 p-2 rounded-xl bg-white border border-slate-100 shadow-2xl opacity-0 group-hover/info:opacity-100 transition-opacity z-50 pointer-events-none">
            <p className="text-[9px] text-slate-500 leading-tight">
              Outer ring represents sub-directories. Inner ring shows parent modules. The wider the
              segment, the more commits in that area.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
