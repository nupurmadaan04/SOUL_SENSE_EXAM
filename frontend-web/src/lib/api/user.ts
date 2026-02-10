import { apiClient } from './client';

export const userApi = {
  async getAuditLogs(page: number = 1, limit: number = 20) {
    const token = localStorage.getItem('token');

    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      return await apiClient(`/users/me/audit-logs?page=${page}&per_page=${limit}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error: any) {
      if (error.status === 401) {
        window.location.href = '/login'; // Redirect if unauthorized
        throw new Error('Unauthorized');
      }
      throw error;
    }
  },
};
