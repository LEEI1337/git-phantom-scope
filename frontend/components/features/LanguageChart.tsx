'use client';

import type { LanguageStat } from '../../lib/types';

interface LanguageChartProps {
  readonly languages: ReadonlyArray<LanguageStat>;
}

const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3572A5',
  JavaScript: '#F1E05A',
  TypeScript: '#3178C6',
  Java: '#B07219',
  Go: '#00ADD8',
  Rust: '#DEA584',
  'C++': '#F34B7D',
  C: '#555555',
  'C#': '#178600',
  Ruby: '#701516',
  PHP: '#4F5D95',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  Dart: '#00B4AB',
  Shell: '#89E051',
  HTML: '#E34C26',
  CSS: '#563D7C',
  Lua: '#000080',
  Scala: '#C22D40',
  R: '#198CE7',
};

export default function LanguageChart({ languages }: LanguageChartProps) {
  const topLanguages = languages.slice(0, 8);
  const maxPercentage = Math.max(...topLanguages.map((l) => l.percentage), 1);

  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Languages</h3>

      {/* Stacked bar */}
      <div className="w-full h-4 rounded-full overflow-hidden flex mb-6">
        {topLanguages.map((lang) => (
          <div
            key={lang.name}
            className="h-full transition-all"
            style={{
              width: `${lang.percentage}%`,
              backgroundColor: lang.color || LANGUAGE_COLORS[lang.name] || '#8B949E',
            }}
            title={`${lang.name}: ${lang.percentage.toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Individual bars */}
      <div className="space-y-3">
        {topLanguages.map((lang) => {
          const color = lang.color || LANGUAGE_COLORS[lang.name] || '#8B949E';
          return (
            <div key={lang.name} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm text-gps-text w-24 shrink-0">{lang.name}</span>
              <div className="flex-1 bg-gps-bg rounded-full h-2 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(lang.percentage / maxPercentage) * 100}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
              <span className="text-sm font-mono text-gps-text-secondary w-14 text-right">
                {lang.percentage.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
