import { apiClient } from './client';
import { ExamResult } from '@/types/results';

export interface ExamAnswer {
  question_id: number;
  value: number;
}

export interface ExamSubmissionRequest {
  answers: ExamAnswer[];
  reflection?: string;
  duration_seconds: number;
}

export interface ExamSubmissionResponse {
  id: number;
  total_score: number;
  sentiment_score?: number;
  reflection?: string;
  timestamp: string;
}

export const examsApi = {
  async submitExam(data: ExamSubmissionRequest): Promise<ExamSubmissionResponse> {
    return apiClient('/exams', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  },

  async getExamResult(id: number): Promise<ExamResult> {
    return apiClient(`/exams/${id}`, {
      method: 'GET',
    });
  },

  async getExamResults(): Promise<ExamResult[]> {
    return apiClient('/exams', {
      method: 'GET',
    });
  },
};