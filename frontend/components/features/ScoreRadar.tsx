'use client';

import type { ProfileScores } from '../../lib/types';

interface ScoreRadarProps {
  readonly scores: ProfileScores;
}

const DIMENSIONS = [
  { key: 'activity' as const, label: 'Activity', color: '#58A6FF' },
  { key: 'collaboration' as const, label: 'Collaboration', color: '#238636' },
  { key: 'stack_diversity' as const, label: 'Stack Diversity', color: '#8B5CF6' },
  { key: 'ai_savviness' as const, label: 'AI Savviness', color: '#F97316' },
];

export default function ScoreRadar({ scores }: ScoreRadarProps) {
  const overall = Math.round(
    Object.values(scores).reduce((a, b) => a + b, 0) / 4
  );

  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Dimension Scores</h3>

      {/* Score bars */}
      <div className="space-y-4">
        {DIMENSIONS.map(({ key, label, color }) => {
          const value = scores[key] ?? 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gps-text">{label}</span>
                <span className="font-mono font-bold" style={{ color }}>
                  {value}
                </span>
              </div>
              <div className="w-full bg-gps-bg rounded-full h-3 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${value}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall */}
      <div className="mt-6 pt-4 border-t border-gps-border flex items-center justify-between">
        <span className="text-gps-text-secondary">Overall Score</span>
        <div className="flex items-center gap-2">
          <span className="text-3xl font-bold text-gps-accent">{overall}</span>
          <span className="text-gps-text-secondary text-sm">/100</span>
        </div>
      </div>
    </div>
  );
}
