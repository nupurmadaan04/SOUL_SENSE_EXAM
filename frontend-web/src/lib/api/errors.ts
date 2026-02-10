export interface ApiErrorDetail {
  code?: string;
  message?: string;
  details?: Record<string, any>;
}

export class ApiError extends Error {
  status: number;
  data: any;
  detail?: ApiErrorDetail;
  isNetworkError?: boolean;

  constructor(status: number, data: any) {
    // Try to extract a meaningful message
    let message = 'API Error';
    if (typeof data === 'string') {
      message = data;
    } else if (data?.detail) {
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (data.detail.message) {
        message = data.detail.message;
      }
    } else if (data?.message) {
      message = data.message;
    }

    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;

    if (data?.detail && typeof data.detail === 'object') {
      this.detail = data.detail as ApiErrorDetail;
    }

    if (data?.isNetworkError) {
      this.isNetworkError = true;
    }
  }
}
