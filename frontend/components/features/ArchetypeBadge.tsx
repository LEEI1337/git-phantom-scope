'use client';

import type { DeveloperArchetype } from '../../lib/types';

interface ArchetypeBadgeProps {
  readonly archetype: DeveloperArchetype;
}

const ARCHETYPE_ICONS: Record<string, string> = {
  ai_indie_hacker: '🤖',
  open_source_maintainer: '🌍',
  full_stack_polyglot: '🔀',
  backend_architect: '🏗️',
  frontend_craftsman: '🎨',
  devops_specialist: '⚙️',
  data_scientist: '📊',
  security_sentinel: '🛡️',
  rising_developer: '🚀',
  code_explorer: '🔍',
};

const ARCHETYPE_COLORS: Record<string, string> = {
  ai_indie_hacker: 'from-orange-500 to-red-500',
  open_source_maintainer: 'from-green-500 to-emerald-600',
  full_stack_polyglot: 'from-purple-500 to-indigo-600',
  backend_architect: 'from-blue-500 to-cyan-600',
  frontend_craftsman: 'from-pink-500 to-rose-600',
  devops_specialist: 'from-gray-500 to-zinc-600',
  data_scientist: 'from-teal-500 to-cyan-600',
  security_sentinel: 'from-red-500 to-amber-600',
  rising_developer: 'from-yellow-500 to-orange-500',
  code_explorer: 'from-indigo-500 to-blue-600',
};

export default function ArchetypeBadge({ archetype }: ArchetypeBadgeProps) {
  const icon = ARCHETYPE_ICONS[archetype.id] || '💻';
  const gradient = ARCHETYPE_COLORS[archetype.id] || 'from-gray-500 to-gray-700';
  const confidence = archetype.confidence ? Math.round(archetype.confidence * 100) : null;

  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6 h-full flex flex-col">
      <h3 className="text-lg font-semibold mb-4">Developer Archetype</h3>

      <div className={`bg-gradient-to-br ${gradient} rounded-lg p-6 text-center flex-1 flex flex-col justify-center`}>
        <div className="text-5xl mb-3">{icon}</div>
        <div className="text-xl font-bold text-white">{archetype.name}</div>
        {confidence !== null && (
          <div className="text-sm text-white/70 mt-1">
            {confidence}% confidence
          </div>
        )}
      </div>

      <p className="text-sm text-gps-text-secondary mt-4">
        {archetype.description}
      </p>

      {archetype.alternatives && archetype.alternatives.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gps-border">
          <span className="text-xs text-gps-text-secondary">Also matches: </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {archetype.alternatives.map((alt) => (
              <span
                key={alt}
                className="text-xs px-2 py-0.5 bg-gps-bg rounded border border-gps-border text-gps-text-secondary"
              >
                {ARCHETYPE_ICONS[alt] || '💻'} {alt.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
