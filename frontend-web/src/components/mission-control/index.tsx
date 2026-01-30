'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutGrid, List, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui';
import { KanbanBoard } from './kanban-board';
import { DataGrid } from './data-grid';
import { DataFilters } from './filters';
import { MissionItem, MissionControlData } from './types';
import { MOCK_DASHBOARD_DATA } from '@/lib/dashboard-mock-data';

interface MissionControlProps {
  className?: string;
}

export const MissionControl: React.FC<MissionControlProps> = ({ className }) => {
  const [viewMode, setViewMode] = useState<'board' | 'list'>('board');
  const [data, setData] = useState<MissionControlData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<{
    priorities: string[];
    status: string[];
    domains: string[];
  }>({
    priorities: [],
    status: [],
    domains: [],
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1'}/community/mission-control`
      );
      if (response.ok) {
        const jsonData = await response.json();
        setData(jsonData);
      } else {
        throw new Error('API Error');
      }
    } catch (error) {
      console.warn('Mission Control API unavailable, using mock fallback:', error);
      // Fallback to mock data with type assertion since mock data is now aligned
      setData(MOCK_DASHBOARD_DATA.missionControl as unknown as MissionControlData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filter Logic
  const filteredItems = React.useMemo(() => {
    if (!data) return [];

    return data.items.filter((item) => {
      // Search
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matches =
          item.title.toLowerCase().includes(query) ||
          item.id.toLowerCase().includes(query) ||
          item.number.toString().includes(query) ||
          item.assignee?.login.toLowerCase().includes(query) ||
          false;

        if (!matches) return false;
      }

      // Categories
      if (filters.priorities.length > 0 && !filters.priorities.includes(item.priority))
        return false;
      if (filters.status.length > 0 && !filters.status.includes(item.status)) return false;
      if (filters.domains.length > 0 && !filters.domains.includes(item.domain)) return false;

      return true;
    });
  }, [data, searchQuery, filters]);

  const handleFilterChange = (type: keyof typeof filters, value: string) => {
    setFilters((prev) => {
      const existing = prev[type];
      const next = existing.includes(value)
        ? existing.filter((i) => i !== value)
        : [...existing, value];
      return { ...prev, [type]: next };
    });
  };

  const resetFilters = () => {
    setFilters({
      priorities: [],
      status: [],
      domains: [],
    });
  };

  return (
    <div className={`flex flex-col h-full gap-4 ${className}`}>
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-primary/10 rounded-lg">
            <LayoutGrid className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight">Mission Control</h2>
            <p className="text-xs text-muted-foreground">Global Operations Center</p>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <DataFilters
            onSearch={setSearchQuery}
            filters={filters}
            onFilterChange={handleFilterChange}
            onReset={resetFilters}
          />

          <div className="h-8 w-px bg-border/40 mx-1 hidden sm:block" />

          <div className="flex bg-muted/30 p-1 rounded-xl border border-border/40">
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 px-3 gap-2 rounded-lg transition-all ${
                viewMode === 'board'
                  ? 'bg-white dark:bg-slate-800 text-primary shadow-sm font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setViewMode('board')}
            >
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden sm:inline">Board</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 px-3 gap-2 rounded-lg transition-all ${
                viewMode === 'list'
                  ? 'bg-white dark:bg-slate-800 text-primary shadow-sm font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Table</span>
            </Button>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={fetchData}
            disabled={loading}
            className="h-9 w-9"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-[500px] relative">
        <AnimatePresence mode="wait">
          {loading && !data ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-50 min-h-[300px]"
            >
              <div className="flex flex-col items-center gap-2">
                <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                <span className="text-sm text-muted-foreground font-medium animate-pulse">
                  Establishing uplink...
                </span>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key={viewMode}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {viewMode === 'board' ? (
                <KanbanBoard items={filteredItems} />
              ) : (
                <DataGrid items={filteredItems} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
