import { apiClient } from './client';
import { getSession } from '@/lib/utils/sessionStorage';
import { ExamResult, ResultsHistory } from '@/types/results';
import { ApiError } from './errors';

type AssessmentSummary = {
  id: number;
  total_score: number;
  sentiment_score?: number | null;
  age?: number | null;
  detailed_age_group?: string | null;
  timestamp: string;
};

type AssessmentListResponse = {
  total: number;
  assessments: AssessmentSummary[];
  page: number;
  page_size: number;
};

type AssessmentDetailResponse = {
  id: number;
  total_score: number;
  sentiment_score?: number | null;
  reflection_text?: string | null;
  is_rushed?: boolean | null;
  is_inconsistent?: boolean | null;
  age?: number | null;
  detailed_age_group?: string | null;
  timestamp: string;
  responses_count?: number | null;
};

const getAuthHeaders = () => {
  const token = localStorage.getItem('token') || getSession()?.token;

  if (!token) {
    throw new Error('Not authenticated');
  }

  return {
    Authorization: `Bearer ${token}`,
  };
};

const mapAssessmentToExamResult = (assessment: AssessmentSummary): ExamResult => {
  return {
    id: assessment.id,
    overall_score: assessment.total_score,
    categories: [],
    recommendations: [],
    completed_at: assessment.timestamp,
    duration_seconds: 0,
  };
};

const mapAssessmentDetailToExamResult = (assessment: AssessmentDetailResponse): ExamResult => {
  return {
    id: assessment.id,
    overall_score: assessment.total_score,
    categories: [],
    recommendations: [],
    completed_at: assessment.timestamp,
    duration_seconds: 0,
    reflection: assessment.reflection_text || undefined,
  };
};

export const resultsApi = {
  async getHistory(page: number = 1, pageSize: number = 50): Promise<ResultsHistory> {
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    };

    const response = await apiClient<AssessmentListResponse>(
      `/exams/history?page=${page}&page_size=${pageSize}`,
      {
        method: 'GET',
        headers,
      }
    );

    return {
      total: response.total,
      results: response.assessments.map(mapAssessmentToExamResult),
      page: response.page,
      per_page: response.page_size,
    };
  },

  async getResult(id: string | number): Promise<ExamResult> {
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    };

    try {
      return await apiClient<ExamResult>(`/exams/${id}/results`, {
        method: 'GET',
        headers,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        const assessment = await apiClient<AssessmentDetailResponse>(`/assessments/${id}`, {
          method: 'GET',
          headers,
        });
        return mapAssessmentDetailToExamResult(assessment);
      }

      throw error;
    }
  },
};
