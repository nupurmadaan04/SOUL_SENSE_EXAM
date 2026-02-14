import { apiClient } from './client';

export interface QuestionOption {
  value: number;
  label: string;
}

export interface Question {
  id: number;
  text: string;
  category: string;
  options: QuestionOption[];
}

export interface QuestionsResponse {
  questions: Question[];
}

export const questionsApi = {
  async getQuestions(params?: {
    category?: string;
    count?: number;
  }): Promise<QuestionsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.category) {
      queryParams.append('category', params.category);
    }
    if (params?.count) {
      queryParams.append('count', params.count.toString());
    }

    const queryString = queryParams.toString();
    const endpoint = `/questions${queryString ? `?${queryString}` : ''}`;

    return apiClient(endpoint, {
      method: 'GET',
    });
  },
};