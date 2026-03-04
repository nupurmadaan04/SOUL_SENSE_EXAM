'use client';

import React from 'react';
import { Card, CardHeader, CardContent, CardFooter, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui';
import { Goal } from '@/lib/api/goals';
import { format } from 'date-fns';
import { Target, CheckCircle2, Clock } from 'lucide-react';

interface GoalCardProps {
    goal: Goal;
    onUpdate: (id: number, current_value: number) => void;
    onDelete: (id: number) => void;
}

export const GoalCard: React.FC<GoalCardProps> = ({ goal, onUpdate, onDelete }) => {
    const isCompleted = goal.status === 'completed';
    const progress = goal.progress_percentage;

    const handleQuickProgress = (increment: number) => {
        onUpdate(goal.id, goal.current_value + increment);
    };

    return (
        <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-primary">
            <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                    <div className="space-y-1">
                        <CardTitle className="text-lg font-bold flex items-center gap-2">
                            {goal.title}
                            {isCompleted && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                        </CardTitle>
                        <div className="flex gap-2 items-center">
                            <Badge variant="secondary" className="text-[10px] uppercase">
                                {goal.category}
                            </Badge>
                            {isCompleted && (
                                <Badge variant="success" className="text-[10px] uppercase">
                                    Completed
                                </Badge>
                            )}
                        </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => onDelete(goal.id)} className="text-muted-foreground hover:text-destructive">
                        <Target className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <div className="flex justify-between text-xs font-medium">
                        <span>Progress ({goal.current_value} / {goal.target_value} {goal.unit})</span>
                        <span className={progress >= 100 ? "text-green-500" : "text-primary"}>
                            {Math.round(progress)}%
                        </span>
                    </div>
                    <Progress value={progress} className="h-2" />
                </div>

                {goal.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2 italic">"{goal.description}"</p>
                )}

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    {goal.deadline && (
                        <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>Due {format(new Date(goal.deadline), 'MMM d, yyyy')}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-1">
                        <Target className="w-3 h-3" />
                        <span>Updated {format(new Date(goal.updated_at), 'MMM d')}</span>
                    </div>
                </div>
            </CardContent>
            {!isCompleted && (
                <CardFooter className="pt-0 flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleQuickProgress(1)}
                    >
                        +1 Step
                    </Button>
                    <Button
                        variant="secondary"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleQuickProgress(10)}
                    >
                        +10%
                    </Button>
                </CardFooter>
            )}
        </Card>
    );
};
