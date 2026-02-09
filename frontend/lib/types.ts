/**
 * Git Phantom Scope — Explore Page Types
 *
 * Shared TypeScript interfaces for profile analysis results.
 */

export interface ProfileScores {
  readonly activity: number;
  readonly collaboration: number;
  readonly stack_diversity: number;
  readonly ai_savviness: number;
}

export interface DeveloperArchetype {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly confidence?: number;
  readonly alternatives?: ReadonlyArray<string>;
}

export interface AIAnalysis {
  readonly overall_bucket: string;
  readonly detected_tools: ReadonlyArray<string>;
  readonly confidence: string;
  readonly burst_score?: number;
  readonly ai_config_files?: ReadonlyArray<string>;
}

export interface LanguageStat {
  readonly name: string;
  readonly percentage: number;
  readonly color?: string;
}

export interface RepoSummary {
  readonly name: string;
  readonly language: string | null;
  readonly stars: number;
  readonly forks?: number;
  readonly description: string;
}

export interface TechProfile {
  readonly languages: ReadonlyArray<LanguageStat>;
  readonly frameworks: ReadonlyArray<string>;
  readonly top_repos: ReadonlyArray<RepoSummary>;
}

export interface ProfileResult {
  readonly session_id: string;
  readonly profile: {
    readonly username: string;
    readonly avatar_url: string;
    readonly bio: string | null;
    readonly stats: {
      readonly repos: number;
      readonly followers: number;
      readonly contributions_last_year: number;
    };
  };
  readonly scores: ProfileScores;
  readonly archetype: DeveloperArchetype;
  readonly ai_analysis: AIAnalysis;
  readonly tech_profile: TechProfile;
  readonly meta: {
    readonly request_id: string;
    readonly cache_hit: boolean;
  };
}

export interface InsightDataPoint {
  readonly language?: string;
  readonly archetype?: string;
  readonly model?: string;
  readonly date?: string;
  readonly count?: number;
  readonly sample_size?: number;
  readonly buckets?: Record<string, number>;
}

export interface InsightsData {
  readonly metric: string;
  readonly period: string;
  readonly data: ReadonlyArray<InsightDataPoint>;
  readonly updated_at: string;
  readonly meta: Record<string, unknown>;
}
