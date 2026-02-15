export interface CategoryScore {
    name: string;
    score: number;
    max_score: number;
    description?: string;
}

export interface Recommendation {
    id: number;
    title: string;
    description: string;
    category?: string;
    priority?: "high" | "medium" | "low";
}

export interface ExamResult {
    id: number;
    overall_score: number;
    total_score?: number; // For backward compatibility
    sentiment_score?: number;
    categories: CategoryScore[];
    recommendations: Recommendation[];
    completed_at: string;
    timestamp?: string; // For backward compatibility
    duration_seconds: number;
    reflection?: string;
}

export interface ResultsHistory {
    results: ExamResult[];
    total: number;
    page: number;
    per_page: number;
}
