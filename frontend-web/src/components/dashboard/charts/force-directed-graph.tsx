'use client';

import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui';
import { Share2, Maximize2, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

interface Node {
  id: string;
  group: 'user' | 'module';
  val: number;
  x?: number;
  y?: number;
}

interface Link {
  source: string;
  target: string;
  value: number;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export function ForceDirectedGraph({ data }: { data: GraphData }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 0, height: 400 });

  useEffect(() => {
    if (containerRef.current) {
      const updateDimensions = () => {
        setDimensions({
          width: containerRef.current?.offsetWidth || 0,
          height: 400,
        });
      };
      updateDimensions();
      window.addEventListener('resize', updateDimensions);
      return () => window.removeEventListener('resize', updateDimensions);
    }
  }, []);

  // Format data for react-force-graph
  const graphData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    };
  }, [data]);

  return (
    <Card className="col-span-full lg:col-span-4 bg-white border-slate-200 shadow-xl rounded-3xl overflow-hidden group relative">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="space-y-1">
          <CardTitle className="text-xl font-black tracking-tighter flex items-center gap-2 text-slate-900">
            <Share2 className="h-5 w-5 text-blue-600" />
            CONSTELLATION_MAP
          </CardTitle>
          <CardDescription className="text-xs font-medium text-slate-500">
            Visualizing the gravitational pull of contributors on repository modules.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <div className="px-2 py-1 rounded-full bg-blue-50 border border-blue-100 text-[10px] font-black text-blue-600 flex items-center gap-1 uppercase">
            <Zap className="h-3 w-3" />
            Live_Pulse
          </div>
        </div>
      </CardHeader>

      <div className="px-6 py-2 border-y border-slate-100 bg-blue-50/30">
        <p className="text-[10px] leading-relaxed text-slate-600 font-medium italic">
          <span className="text-blue-600 font-bold uppercase tracking-tighter mr-2">
            Why this exists:
          </span>
          This graph represents the **community&apos;s knowledge structure**. Nodes migrate toward
          the folders they touch most. Tighter clusters indicate highly collaborative modules.
        </p>
      </div>

      <CardContent className="p-0 relative" ref={containerRef}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_white,_transparent)] pointer-events-none" />

        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            ref={fgRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeLabel="id"
            nodeColor={(node: any) => (node.group === 'user' ? '#2563EB' : '#7C3AED')}
            nodeRelSize={6}
            nodeVal={(node: any) => node.val}
            linkColor={() => 'rgba(0, 0, 0, 0.08)'}
            linkWidth={(link: any) => Math.sqrt(link.value)}
            backgroundColor="#ffffff"
            onNodeClick={(node: any) => {
              fgRef.current.centerAt(node.x, node.y, 1000);
              fgRef.current.zoom(3, 1000);
            }}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const label = node.id;
              const fontSize = 12 / globalScale;
              ctx.font = `${fontSize}px Inter`;

              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, node.val / 2 + 1, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.group === 'user' ? '#2563EB' : '#7C3AED';
              ctx.fill();

              // Subtle shadow for depth
              ctx.shadowBlur = 4;
              ctx.shadowColor = 'rgba(0,0,0,0.1)';

              // Label (Dark text for white background)
              if (globalScale > 1.5) {
                ctx.fillStyle = '#1E293B';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(label, node.x, node.y + node.val / 2 + 5);
              }
            }}
          />
        ) : (
          <div className="h-[400px] flex items-center justify-center text-slate-400 font-medium italic">
            Gathering community topology...
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 left-6 flex items-center gap-6 pointer-events-none">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-blue-600 shadow-sm" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-none">
              Contributor
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-purple-600 shadow-sm" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-none">
              Code Module
            </span>
          </div>
        </div>

        <div className="absolute bottom-4 right-6 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
          Drag to explore • Click to focus
        </div>
      </CardContent>
    </Card>
  );
}
