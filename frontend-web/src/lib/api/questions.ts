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

  async generatePersonalizedAssessment(payload: {
    user_context?: Record<string, any>;
    assessment_type?: 'holistic_eq' | 'stress_resilience' | 'relationships_empathy' | 'reflection_triggers' | 'personalized_custom' | string;
    count?: number;
    tone?: string;
  }): Promise<{ assessment_type: string; total: number; questions: Question[] }> {
    return apiClient('/questions/generate-personalized', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};