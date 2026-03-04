'use client';

import React, { useState } from 'react';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { GoalCreate } from '@/lib/api/goals';

interface GoalFormProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: GoalCreate) => void;
    isLoading?: boolean;
}

const CATEGORIES = [
    'Resilience', 'Empathy', 'Self-Awareness', 'Self-Regulation',
    'Social Skills', 'Mindfulness', 'Motivation', 'Other'
];

export const GoalForm: React.FC<GoalFormProps> = ({ isOpen, onClose, onSubmit, isLoading }) => {
    const [formData, setFormData] = useState<GoalCreate>({
        title: '',
        description: '',
        category: 'Resilience',
        target_value: 100,
        unit: 'percentage',
        deadline: undefined
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit(formData);
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Create New Emotional Goal"
        >
            <form onSubmit={handleSubmit} className="space-y-4 py-4">
                <div className="space-y-2">
                    <Label htmlFor="title">Goal Title</Label>
                    <Input
                        id="title"
                        placeholder="e.g., Practice daily mindfulness"
                        value={formData.title}
                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        required
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="category">Category</Label>
                    <Select
                        value={formData.category}
                        onValueChange={(val) => setFormData({ ...formData, category: val })}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                        <SelectContent>
                            {CATEGORIES.map(cat => (
                                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="target">Target Value</Label>
                        <Input
                            id="target"
                            type="number"
                            value={formData.target_value}
                            onChange={(e) => setFormData({ ...formData, target_value: Number(e.target.value) })}
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="unit">Unit</Label>
                        <Input
                            id="unit"
                            placeholder="e.g., percentage, days"
                            value={formData.unit}
                            onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                            required
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="description">Description (Optional)</Label>
                    <Textarea
                        id="description"
                        placeholder="Describe what success looks like..."
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="deadline">Deadline (Optional)</Label>
                    <Input
                        id="deadline"
                        type="date"
                        onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                    />
                </div>

                <div className="flex justify-end gap-3 pt-4">
                    <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                    <Button type="submit" disabled={isLoading}>
                        {isLoading ? 'Creating...' : 'Set Goal'}
                    </Button>
                </div>
            </form>
        </Modal>
    );
};
