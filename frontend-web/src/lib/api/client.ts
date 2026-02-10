import { ApiError } from './errors';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface RequestOptions extends RequestInit {
  timeout?: number;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeout = 10000, ...fetchOptions } = options;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });

    clearTimeout(id);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: `HTTP Error ${response.status}: ${response.statusText}` };
      }
      throw new ApiError(response.status, errorData);
    }

    // Handle empty response (204 No Content)
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error: any) {
    clearTimeout(id);

    if (error.name === 'AbortError') {
      throw new ApiError(408, {
        message: 'Request timed out. Please check your internet connection.',
        isNetworkError: true,
      });
    }

    if (error instanceof ApiError) {
      throw error;
    }

    // Likely a network error (DNS, Connection Refused, etc.)
    throw new ApiError(0, {
      message: 'Network connection failed. Please check if you are online.',
      isNetworkError: true,
      originalError: error.message,
    });
  }
}
