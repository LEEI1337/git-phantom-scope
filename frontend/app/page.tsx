'use client';

import { useState } from 'react';

export default function HomePage() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
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

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-4 pt-20 pb-16">
        <h1 className="text-5xl font-bold text-center mb-4">
          <span className="text-gps-accent">Git</span> Phantom{' '}
          <span className="text-gps-green">Scope</span>
        </h1>
        <p className="text-gps-text-secondary text-xl text-center max-w-2xl mb-8">
          Analyze any GitHub profile. Detect AI-assisted code. Generate stunning
          visual identities. Zero data stored.
        </p>

        {/* Search */}
        <div className="flex gap-3 w-full max-w-lg">
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
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>

        {error && (
          <p className="mt-4 text-red-400 text-sm">{error}</p>
        )}
      </section>

      {/* Results */}
      {result && (
        <section className="px-4 pb-20 max-w-4xl mx-auto w-full">
          <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
            <h2 className="text-2xl font-bold mb-6">
              Profile Analysis
            </h2>

            {/* Scores */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {Object.entries((result as Record<string, unknown>).scores as Record<string, number> || {}).map(
                ([key, value]) => (
                  <div
                    key={key}
                    className="bg-gps-bg border border-gps-border rounded-lg p-4 text-center"
                  >
                    <div className="text-3xl font-bold text-gps-accent">
                      {value}
                    </div>
                    <div className="text-sm text-gps-text-secondary capitalize mt-1">
                      {key.replace('_', ' ')}
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Archetype */}
            {(result as Record<string, unknown>).archetype && (
              <div className="bg-gps-bg border border-gps-border rounded-lg p-4 mb-6">
                <div className="text-sm text-gps-text-secondary">
                  Developer Archetype
                </div>
                <div className="text-xl font-bold text-gps-purple mt-1">
                  {((result as Record<string, unknown>).archetype as Record<string, string>)?.name}
                </div>
                <div className="text-sm text-gps-text-secondary mt-1">
                  {((result as Record<string, unknown>).archetype as Record<string, string>)?.description}
                </div>
              </div>
            )}

            {/* Raw JSON (dev mode) */}
            <details className="mt-4">
              <summary className="cursor-pointer text-gps-text-secondary text-sm hover:text-gps-accent">
                Raw Response (Developer View)
              </summary>
              <pre className="mt-2 p-4 bg-gps-bg border border-gps-border rounded-lg overflow-auto text-xs font-mono">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        </section>
      )}

      {/* Features */}
      {!result && (
        <section className="px-4 pb-20 max-w-6xl mx-auto w-full">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard
              title="Zero Data Storage"
              description="No accounts. No stored data. Session expires in 30 minutes. GDPR by design."
              icon="shield"
            />
            <FeatureCard
              title="AI Code Detection"
              description="Heuristic analysis of commit patterns, co-author tags, and AI tool usage."
              icon="scan"
            />
            <FeatureCard
              title="Visual Identity Package"
              description="Get a complete bundle: README, banner, repo covers, and social cards."
              icon="package"
            />
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-gps-text-secondary text-sm border-t border-gps-border">
        <p>
          Built by{' '}
          <a
            href="https://github.com/LEEI1337"
            className="text-gps-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            @LEEI1337
          </a>
          {' | '}
          Privacy-First {' | '}
          BSL-1.1 License
        </p>
      </footer>
    </main>
  );
}

function FeatureCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6 hover:border-gps-accent transition">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-gps-text-secondary text-sm">{description}</p>
    </div>
  );
}
