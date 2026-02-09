'use client';

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import type { InsightsData } from '../../lib/types';

const METRICS = [
  { id: 'ai_usage_by_language', label: 'AI Usage by Language' },
  { id: 'archetype_distribution', label: 'Archetype Distribution' },
  { id: 'model_popularity', label: 'AI Model Popularity' },
  { id: 'generation_trends', label: 'Generation Trends' },
];

const PERIODS = [
  { id: '7d', label: '7 Days' },
  { id: '30d', label: '30 Days' },
  { id: '90d', label: '90 Days' },
  { id: '1y', label: '1 Year' },
];

const COLORS = [
  '#58A6FF', '#238636', '#8B5CF6', '#F97316', '#EF4444',
  '#06B6D4', '#EC4899', '#14B8A6', '#F59E0B', '#6366F1',
];

export default function InsightsPage() {
  const [metric, setMetric] = useState('ai_usage_by_language');
  const [period, setPeriod] = useState('30d');
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/v1/public/insights?metric=${metric}&period=${period}`
      );
      if (!response.ok) throw new Error('Failed to fetch insights');
      const result: InsightsData = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [metric, period]);

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
            <a href="/explore" className="hover:text-gps-accent transition">Explore</a>
            <a href="/insights" className="text-gps-accent">Insights</a>
          </nav>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-2">Public Insights</h1>
        <p className="text-gps-text-secondary mb-8">
          Aggregated, anonymous trends from developer profile analyses. No personal data stored.
        </p>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-8">
          <div className="flex gap-2">
            {METRICS.map((m) => (
              <button
                key={m.id}
                onClick={() => setMetric(m.id)}
                className={`px-3 py-2 rounded-lg text-sm transition ${
                  metric === m.id
                    ? 'bg-gps-accent text-white'
                    : 'bg-gps-surface text-gps-text-secondary border border-gps-border hover:border-gps-accent'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2 ml-auto">
            {PERIODS.map((p) => (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-3 py-2 rounded-lg text-sm transition ${
                  period === p.id
                    ? 'bg-gps-green text-white'
                    : 'bg-gps-surface text-gps-text-secondary border border-gps-border hover:border-gps-green'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Loading / Error */}
        {loading && (
          <div className="text-center py-20 text-gps-text-secondary">
            <svg className="animate-spin h-8 w-8 mx-auto mb-4 text-gps-accent" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading insights...
          </div>
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {/* Charts */}
        {data && !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Main chart */}
            <div className="bg-gps-surface border border-gps-border rounded-xl p-6 lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">
                {METRICS.find((m) => m.id === metric)?.label}
              </h3>
              {data.data.length === 0 ? (
                <div className="text-center py-12 text-gps-text-secondary">
                  No data available for this period. Analyze some profiles to generate insights!
                </div>
              ) : metric === 'archetype_distribution' ? (
                <ResponsiveContainer width="100%" height={400}>
                  <PieChart>
                    <Pie
                      data={data.data.map((d, i) => ({
                        name: d.archetype || `Item ${i}`,
                        value: d.count || d.sample_size || 1,
                      }))}
                      cx="50%"
                      cy="50%"
                      outerRadius={150}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${(name as string).replace(/_/g, ' ')} (${(percent * 100).toFixed(0)}%)`
                      }
                    >
                      {data.data.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#161B22',
                        border: '1px solid #30363D',
                        borderRadius: '8px',
                        color: '#C9D1D9',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart
                    data={data.data.map((d, i) => ({
                      name: d.language || d.model || d.date || `Item ${i}`,
                      value: d.count || d.sample_size || 0,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
                    <XAxis
                      dataKey="name"
                      stroke="#8B949E"
                      tick={{ fill: '#8B949E', fontSize: 12 }}
                    />
                    <YAxis stroke="#8B949E" tick={{ fill: '#8B949E', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#161B22',
                        border: '1px solid #30363D',
                        borderRadius: '8px',
                        color: '#C9D1D9',
                      }}
                    />
                    <Bar dataKey="value" fill="#58A6FF" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Stats cards */}
            <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gps-text-secondary">Data Points</span>
                  <span className="font-mono text-gps-accent">{data.data.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gps-text-secondary">Period</span>
                  <span className="font-mono">{data.period}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gps-text-secondary">Last Updated</span>
                  <span className="font-mono text-sm">{data.updated_at}</span>
                </div>
              </div>
            </div>

            <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Data Table</h3>
              <div className="overflow-auto max-h-60">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gps-text-secondary border-b border-gps-border">
                      <th className="text-left py-2">Name</th>
                      <th className="text-right py-2">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.data.slice(0, 10).map((d, i) => (
                      <tr key={i} className="border-b border-gps-border/50">
                        <td className="py-2 text-gps-text">
                          {d.language || d.archetype || d.model || d.date || '-'}
                        </td>
                        <td className="py-2 text-right font-mono text-gps-text-secondary">
                          {d.count || d.sample_size || 0}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Privacy note */}
        <div className="mt-8 text-center text-xs text-gps-text-secondary">
          All data is anonymized and aggregated. No personally identifiable information is stored or displayed.
        </div>
      </section>
    </main>
  );
}
