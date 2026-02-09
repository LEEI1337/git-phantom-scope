'use client';

import { useState } from 'react';
import type { ProfileResult } from '../../lib/types';
import ScoreRadar from '../../components/features/ScoreRadar';
import ArchetypeBadge from '../../components/features/ArchetypeBadge';
import AIAnalysisCard from '../../components/features/AIAnalysisCard';
import LanguageChart from '../../components/features/LanguageChart';
import RepoGrid from '../../components/features/RepoGrid';

export default function ExplorePage() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProfileResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/v1/public/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_username: username.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData?.error?.message || 'Analysis failed');
      }

      const data: ProfileResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gps-bg">
      {/* Header */}
      <header className="border-b border-gps-border">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-bold">
            <span className="text-gps-accent">Git</span>{' '}
            <span className="text-gps-text">Phantom</span>{' '}
            <span className="text-gps-green">Scope</span>
          </a>
          <nav className="flex gap-6 text-sm text-gps-text-secondary">
            <a href="/" className="hover:text-gps-accent transition">Home</a>
            <a href="/explore" className="text-gps-accent">Explore</a>
            <a href="/insights" className="hover:text-gps-accent transition">Insights</a>
          </nav>
        </div>
      </header>

      {/* Search */}
      <section className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Explore Developer Profiles</h1>
        <div className="flex gap-3 max-w-xl">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            placeholder="Enter GitHub username..."
            className="flex-1 px-4 py-3 bg-gps-surface border border-gps-border rounded-lg
                       text-gps-text placeholder-gps-text-secondary focus:outline-none
                       focus:border-gps-accent focus:ring-1 focus:ring-gps-accent transition"
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !username.trim()}
            className="px-6 py-3 bg-gps-green text-white font-semibold rounded-lg
                       hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed
                       transition"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analyzing...
              </span>
            ) : 'Analyze'}
          </button>
        </div>
        {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}
      </section>

      {/* Results */}
      {result && (
        <section className="max-w-7xl mx-auto px-4 pb-16">
          {/* Profile Header */}
          <div className="bg-gps-surface border border-gps-border rounded-xl p-6 mb-6 flex items-center gap-6">
            <img
              src={result.profile.avatar_url}
              alt=""
              className="w-20 h-20 rounded-full border-2 border-gps-accent"
            />
            <div>
              <h2 className="text-2xl font-bold">{result.profile.username}</h2>
              {result.profile.bio && (
                <p className="text-gps-text-secondary mt-1">{result.profile.bio}</p>
              )}
              <div className="flex gap-4 mt-2 text-sm text-gps-text-secondary">
                <span>{result.profile.stats.repos} repos</span>
                <span>{result.profile.stats.followers} followers</span>
                <span>{result.profile.stats.contributions_last_year} contributions</span>
              </div>
            </div>
            {result.meta.cache_hit && (
              <span className="ml-auto text-xs bg-gps-bg px-2 py-1 rounded text-gps-text-secondary border border-gps-border">
                cached
              </span>
            )}
          </div>

          {/* Score Grid + Archetype */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2">
              <ScoreRadar scores={result.scores} />
            </div>
            <div>
              <ArchetypeBadge archetype={result.archetype} />
            </div>
          </div>

          {/* AI Analysis + Languages */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <AIAnalysisCard analysis={result.ai_analysis} />
            <LanguageChart languages={result.tech_profile.languages} />
          </div>

          {/* Top Repos */}
          <RepoGrid repos={result.tech_profile.top_repos} />

          {/* Session Info */}
          <div className="mt-6 text-center text-xs text-gps-text-secondary">
            Session: {result.session_id.slice(0, 8)}... | Request: {result.meta.request_id.slice(0, 8)}...
            | Expires in 30 minutes | No data stored
          </div>
        </section>
      )}
    </main>
  );
}
