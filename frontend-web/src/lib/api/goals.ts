import { apiClient } from './client';

export interface Goal {
    id: number;
    user_id: number;
    title: string;
    description?: string;
    category: string;
    target_value: number;
    current_value: number;
    unit: string;
    deadline?: string;
    status: 'active' | 'completed' | 'abandoned' | 'paused';
    progress_percentage: number;
    created_at: string;
    updated_at: string;
}

export interface GoalCreate {
    title: string;
    description?: string;
    category: string;
    target_value?: number;
    unit?: string;
    deadline?: string;
}

export interface GoalUpdate {
    title?: string;
    description?: string;
    category?: string;
    target_value?: number;
    current_value?: number;
    status?: 'active' | 'completed' | 'abandoned' | 'paused';
    deadline?: string;
}

export interface GoalListResponse {
    total: number;
    goals: Goal[];
    page: number;
    page_size: number;
}

export const goalsApi = {
    list: async (status?: string, page: number = 1, pageSize: number = 20) => {
        let url = `/goals/?page=${page}&page_size=${pageSize}`;
        if (status) url += `&status=${status}`;

        return await apiClient.get<GoalListResponse>(url);
    },

    get: async (id: number) => {
        return await apiClient.get<Goal>(`/goals/${id}`);
    },

    create: async (data: GoalCreate) => {
        return await apiClient.post<Goal>('/goals/', data);
    },

    update: async (id: number, data: GoalUpdate) => {
        // @ts-ignore - Patch was just added but typing might not have caught up in IDE
        return await apiClient.patch<Goal>(`/goals/${id}`, data);
    },

    delete: async (id: number) => {
        await apiClient.delete(`/goals/${id}`);
    },

    getStats: async () => {
        return await apiClient.get<any>('/goals/stats');
    }
};
