'use client';

import React, { useState, useEffect } from 'react';
import { goalsApi, Goal, GoalCreate } from '@/lib/api/goals';
import { GoalCard } from '@/components/goals/GoalCard';
import { GoalForm } from '@/components/goals/GoalForm';
import { GoalStats } from '@/components/goals/GoalStats';
import { Button } from '@/components/ui/button';
import { Plus, Loader2, Target, Filter } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function GoalsPage() {
    const [goals, setGoals] = useState<Goal[]>([]);
    const [stats, setStats] = useState({ total_goals: 0, completed_goals: 0, active_goals: 0, success_rate: 0 });
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitLoading, setIsSubmitLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('all');

    const fetchGoals = async () => {
        setIsLoading(true);
        try {
            const statusFilter = activeTab === 'all' ? undefined : activeTab;
            const data = await goalsApi.list(statusFilter);
            setGoals(data.goals);

            const statsData = await goalsApi.getStats();
            setStats(statsData);
        } catch (err) {
            console.error('Failed to fetch goals:', err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchGoals();
    }, [activeTab]);

    const handleCreateGoal = async (data: GoalCreate) => {
        setIsSubmitLoading(true);
        try {
            await goalsApi.create(data);
            setIsModalOpen(false);
            fetchGoals();
        } catch (err) {
            console.error('Failed to create goal:', err);
        } finally {
            setIsSubmitLoading(false);
        }
    };

    const handleUpdateProgress = async (id: number, current_value: number) => {
        try {
            await goalsApi.update(id, { current_value });
            fetchGoals();
        } catch (err) {
            console.error('Failed to update progress:', err);
        }
    };

    const handleDeleteGoal = async (id: number) => {
        if (window.confirm('Are you sure you want to delete this goal?')) {
            try {
                await goalsApi.delete(id);
                fetchGoals();
            } catch (err) {
                console.error('Failed to delete goal:', err);
            }
        }
    };

    return (
        <div className="container mx-auto p-6 max-w-7xl animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-primary">Emotional Growth Goals</h1>
                    <p className="text-muted-foreground mt-1 text-lg">Set markers for your journey and watch your progress unfold.</p>
                </div>
                <Button
                    onClick={() => setIsModalOpen(true)}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-xl transition-all duration-300 gap-2 font-semibold"
                >
                    <Plus className="w-5 h-5" />
                    Set New Goal
                </Button>
            </div>

            <GoalStats stats={stats} />

            <div className="flex flex-col gap-6">
                <div className="flex justify-between items-center">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full md:w-auto">
                        <TabsList className="grid w-full grid-cols-4 md:inline-flex md:w-auto mb-2">
                            <TabsTrigger value="all">View All</TabsTrigger>
                            <TabsTrigger value="active">Active</TabsTrigger>
                            <TabsTrigger value="completed">Completed</TabsTrigger>
                            <TabsTrigger value="paused">Paused</TabsTrigger>
                        </TabsList>
                    </Tabs>
                </div>

                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
                        <Loader2 className="w-12 h-12 animate-spin text-primary/40 mb-4" />
                        <p className="text-lg font-medium">Mapping your coordinates...</p>
                    </div>
                ) : goals.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {goals.map((goal) => (
                            <GoalCard
                                key={goal.id}
                                goal={goal}
                                onUpdate={handleUpdateProgress}
                                onDelete={handleDeleteGoal}
                            />
                        ))}
                    </div>
                ) : (
                    <Card className="border-dashed border-2 bg-muted/30">
                        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                            <div className="bg-primary/10 p-5 rounded-full mb-6">
                                <Target className="w-12 h-12 text-primary/60" />
                            </div>
                            <CardTitle className="text-2xl font-bold mb-2">No goals found here</CardTitle>
                            <p className="text-muted-foreground max-w-sm mb-8 text-lg">
                                Setting goals is the first step in turning the invisible into the visible. Start your growth journey today.
                            </p>
                            <Button onClick={() => setIsModalOpen(true)} variant="outline" size="lg" className="border-primary text-primary hover:bg-primary hover:text-white">
                                Set Your First Goal
                            </Button>
                        </CardContent>
                    </Card>
                )}
            </div>

            <GoalForm
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSubmit={handleCreateGoal}
                isLoading={isSubmitLoading}
            />
        </div>
    );
}
