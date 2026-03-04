'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Target, CheckCircle2, TrendingUp, BarChart, Clock } from 'lucide-react';

interface GoalStatsProps {
    stats: {
        total_goals: number;
        completed_goals: number;
        active_goals: number;
        success_rate: number;
    };
}

export const GoalStats: React.FC<GoalStatsProps> = ({ stats }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card className="bg-primary/5 border-primary/20 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                    <CardTitle className="text-sm font-medium">Total Goals</CardTitle>
                    <BarChart className="h-4 w-4 text-primary" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.total_goals}</div>
                    <p className="text-xs text-muted-foreground mt-1">Lifetime goals set</p>
                </CardContent>
            </Card>

            <Card className="bg-green-500/5 border-green-500/20 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                    <CardTitle className="text-sm font-medium">Completed</CardTitle>
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.completed_goals}</div>
                    <p className="text-xs text-muted-foreground mt-1">Milestones reached</p>
                </CardContent>
            </Card>

            <Card className="bg-blue-500/5 border-blue-500/20 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                    <CardTitle className="text-sm font-medium">Active</CardTitle>
                    <Clock className="h-4 w-4 text-blue-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.active_goals}</div>
                    <p className="text-xs text-muted-foreground mt-1">In progress right now</p>
                </CardContent>
            </Card>

            <Card className="bg-purple-500/5 border-purple-500/20 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                    <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                    <TrendingUp className="h-4 w-4 text-purple-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{Math.round(stats.success_rate)}%</div>
                    <p className="text-xs text-muted-foreground mt-1">Goals completed vs set</p>
                </CardContent>
            </Card>
        </div>
    );
};


