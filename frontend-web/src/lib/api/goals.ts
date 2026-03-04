const API_Base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function authFetch(url: string, options: RequestInit = {}) {
    const token = localStorage.getItem('token');
    if (!token) throw new Error('Not authenticated');

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
    };

    const response = await fetch(`${API_Base}${url}`, { ...options, headers });
    if (!response.ok) {
        if (response.status === 401) window.location.href = '/login';
        throw new Error(await response.text() || 'API request failed');
    }

    // Some endpoints may return 204 No Content
    if (response.status === 204) return null as any;
    return response.json();
}

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
        return authFetch(url);
    },

    get: async (id: number) => {
        return authFetch(`/goals/${id}`);
    },

    create: async (data: GoalCreate) => {
        return authFetch('/goals/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    update: async (id: number, data: GoalUpdate) => {
        return authFetch(`/goals/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    delete: async (id: number) => {
        return authFetch(`/goals/${id}`, { method: 'DELETE' });
    },

    getStats: async () => {
        return authFetch('/goals/stats');
    }
};
