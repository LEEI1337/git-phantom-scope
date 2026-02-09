/**
 * Git Phantom Scope - API Client
 *
 * Centralized API calls for the frontend.
 * All API interactions go through this module.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface AnalyzeRequest {
  github_username: string;
  preferences?: {
    career_goal?: string;
    style?: string;
    colors?: string[];
  };
  byok?: {
    gemini_key?: string;
    openai_key?: string;
  };
}

export interface ProfileScores {
  activity: number;
  collaboration: number;
  stack_diversity: number;
  ai_savviness: number;
}

export interface DeveloperArchetype {
  id: string;
  name: string;
  description: string;
}

export interface AnalyzeResponse {
  session_id: string;
  profile: {
    username: string;
    avatar_url: string;
    bio: string | null;
    stats: {
      repos: number;
      followers: number;
      contributions_last_year: number;
    };
  };
  scores: ProfileScores;
  archetype: DeveloperArchetype;
  ai_analysis: {
    overall_bucket: string;
    detected_tools: string[];
    confidence: string;
  };
  tech_profile: {
    languages: Array<{ name: string; percentage: number }>;
    frameworks: string[];
    top_repos: Array<{
      name: string;
      language: string | null;
      stars: number;
      description: string;
    }>;
  };
  meta: {
    request_id: string;
    cache_hit: boolean;
  };
}

export interface GenerateRequest {
  session_id: string;
  template_id: string;
  model_preferences?: {
    text_model?: string;
    image_model?: string;
  };
  assets: string[];
}

export interface GenerateResponse {
  job_id: string;
  status: string;
  estimated_time_seconds: number;
}

export interface ValidateKeyRequest {
  provider: string;
  api_key: string;
}

export interface ValidateKeyResponse {
  valid: boolean;
  tier?: string;
  rate_limits?: {
    requests_per_minute: number;
    requests_per_day: number;
  };
  features?: {
    text_generation: boolean;
    image_generation: boolean;
  };
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error?.error?.message || `API error: ${response.status}`
      );
    }

    return response.json();
  }

  async analyzeProfile(req: AnalyzeRequest): Promise<AnalyzeResponse> {
    return this.request<AnalyzeResponse>('/api/v1/public/analyze', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async generatePackage(req: GenerateRequest): Promise<GenerateResponse> {
    return this.request<GenerateResponse>('/api/v1/public/generate', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async getJobStatus(jobId: string): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/public/generate/${jobId}`);
  }

  async validateKey(req: ValidateKeyRequest): Promise<ValidateKeyResponse> {
    return this.request<ValidateKeyResponse>('/api/v1/keys/validate', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async getInsights(
    metric: string = 'ai_usage_by_language',
    period: string = '30d'
  ): Promise<Record<string, unknown>> {
    return this.request(
      `/api/v1/public/insights?metric=${metric}&period=${period}`
    );
  }

  async healthCheck(): Promise<{ status: string }> {
    return this.request('/health');
  }
}

export const apiClient = new APIClient();
export default apiClient;
