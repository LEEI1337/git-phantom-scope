'use client';

import type { AIAnalysis } from '../../lib/types';

interface AIAnalysisCardProps {
  readonly analysis: AIAnalysis;
}

const BUCKET_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  heavy: { label: 'Heavy AI User', color: '#F97316', icon: '🔥' },
  moderate: { label: 'Moderate AI User', color: '#8B5CF6', icon: '⚡' },
  light: { label: 'Light AI User', color: '#58A6FF', icon: '💡' },
  none: { label: 'No AI Detected', color: '#8B949E', icon: '🔒' },
};

const TOOL_ICONS: Record<string, string> = {
  copilot: '🤖',
  cursor: '📝',
  windsurf: '🏄',
  aider: '🔧',
  claude: '🟠',
  chatgpt: '💬',
  gemini: '♊',
  tabnine: '📐',
  codeium: '⚡',
};

export default function AIAnalysisCard({ analysis }: AIAnalysisCardProps) {
  const bucket = BUCKET_LABELS[analysis.overall_bucket] || BUCKET_LABELS.none;

  return (
    <div className="bg-gps-surface border border-gps-border rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">AI Analysis</h3>

      {/* Bucket badge */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-3xl">{bucket.icon}</span>
        <div>
          <div className="font-bold text-lg" style={{ color: bucket.color }}>
            {bucket.label}
          </div>
          <div className="text-sm text-gps-text-secondary">
            Confidence: {analysis.confidence}
          </div>
        </div>
      </div>

      {/* Burst score */}
      {analysis.burst_score !== undefined && analysis.burst_score > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gps-text-secondary">Burst Score</span>
            <span className="font-mono">{analysis.burst_score}</span>
          </div>
          <div className="w-full bg-gps-bg rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full bg-gps-orange transition-all"
              style={{ width: `${Math.min(analysis.burst_score, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Detected tools */}
      {analysis.detected_tools.length > 0 && (
        <div>
          <div className="text-sm text-gps-text-secondary mb-2">Detected Tools</div>
          <div className="flex flex-wrap gap-2">
            {analysis.detected_tools.map((tool) => (
              <span
                key={tool}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-gps-bg
                           border border-gps-border rounded-lg text-sm"
              >
                <span>{TOOL_ICONS[tool.toLowerCase()] || '🔧'}</span>
                <span className="capitalize">{tool}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* AI config files */}
      {analysis.ai_config_files && analysis.ai_config_files.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gps-border">
          <div className="text-sm text-gps-text-secondary mb-2">AI Config Files</div>
          <div className="space-y-1">
            {analysis.ai_config_files.map((file) => (
              <div key={file} className="text-xs font-mono text-gps-text-secondary bg-gps-bg px-2 py-1 rounded">
                📄 {file}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
