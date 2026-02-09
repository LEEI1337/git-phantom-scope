'use client';

import type { RepoSummary } from '../../lib/types';

interface RepoGridProps {
  readonly repos: ReadonlyArray<RepoSummary>;
}

const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3572A5',
  JavaScript: '#F1E05A',
  TypeScript: '#3178C6',
  Java: '#B07219',
  Go: '#00ADD8',
  Rust: '#DEA584',
  'C++': '#F34B7D',
  Ruby: '#701516',
  PHP: '#4F5D95',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  Shell: '#89E051',
};

export default function RepoGrid({ repos }: RepoGridProps) {
  if (!repos || repos.length === 0) return null;

  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Top Repositories</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {repos.slice(0, 6).map((repo) => (
          <div
            key={repo.name}
            className="bg-gps-bg border border-gps-border rounded-lg p-4
                       hover:border-gps-accent transition"
          >
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-gps-text-secondary shrink-0" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z" />
              </svg>
              <span className="text-sm font-semibold text-gps-accent truncate">
                {repo.name}
              </span>
            </div>
            <p className="text-xs text-gps-text-secondary line-clamp-2 mb-3 min-h-[2rem]">
              {repo.description || 'No description'}
            </p>
            <div className="flex items-center gap-3 text-xs text-gps-text-secondary">
              {repo.language && (
                <span className="flex items-center gap-1">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: LANGUAGE_COLORS[repo.language] || '#8B949E',
                    }}
                  />
                  {repo.language}
                </span>
              )}
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" />
                </svg>
                {repo.stars}
              </span>
              {repo.forks !== undefined && (
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z" />
                  </svg>
                  {repo.forks}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
