import React from 'react';
import { ExperimentState } from '../types';

interface LossChartProps {
  state: ExperimentState;
}

export const LossChart: React.FC<LossChartProps> = ({ state }) => {
  const history = state.loss_history;
  const width = 640;
  const height = 220;
  const padding = { top: 25, right: 30, bottom: 35, left: 45 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxLoss = 40; // Scale 0 to 40%

  let points = '';
  let rerouteX: number | null = null;

  if (history.length > 0) {
    const minSeq = history[0].seq;
    const maxSeq = Math.max(minSeq + 20, history[history.length - 1].seq);
    const seqRange = Math.max(1, maxSeq - minSeq);

    points = history
      .map((pt, idx) => {
        const x = padding.left + ((pt.seq - minSeq) / seqRange) * plotWidth;
        const y = padding.top + plotHeight - (Math.min(pt.loss_rate, maxLoss) / maxLoss) * plotHeight;
        if (pt.path.includes('ALTERNATE') && rerouteX === null) {
          rerouteX = x;
        }
        return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  }

  return (
    <div className="card" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Real-Time Packet Loss Curve
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Empirical loss % measured dynamically across packet transmission sequence
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '14px', fontSize: '0.75rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
            <span style={{ width: '12px', height: '3px', background: state.total_lost > 0 ? '#f43f5e' : '#10b981', display: 'inline-block', borderRadius: '1px' }} />
            Measured Loss Rate %
          </span>
          {rerouteX !== null && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981' }}>
              <span style={{ width: '12px', height: '0px', borderTop: '2px solid #10b981', display: 'inline-block' }} />
              Rerouted to Alternate (s3)
            </span>
          )}
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative', minHeight: '180px', background: 'var(--bg-surface-subtle)', borderRadius: '8px', border: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%' }}>
          {/* Y Grid lines */}
          {[0, 10, 20, 30, 40].map((val) => {
            const y = padding.top + plotHeight - (val / maxLoss) * plotHeight;
            return (
              <g key={val}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#1e293b" strokeWidth="1" />
                <text x={padding.left - 8} y={y + 4} fill="#64748b" fontSize="10" textAnchor="end" className="mono">
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Reroute vertical marker */}
          {rerouteX !== null && (
            <g>
              <line
                x1={rerouteX}
                y1={padding.top}
                x2={rerouteX}
                y2={padding.top + plotHeight}
                stroke="#10b981"
                strokeWidth="1.5"
                strokeDasharray="3,3"
              />
              <text x={rerouteX + 4} y={padding.top + 14} fill="#10b981" fontSize="10" fontWeight="600">
                SDN Reroute Triggered
              </text>
            </g>
          )}

          {/* Loss rate path */}
          {points && (
            <path
              d={points}
              fill="none"
              stroke={state.total_lost > 0 && !rerouteX ? '#f43f5e' : (rerouteX ? '#10b981' : '#3b82f6')}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Axes */}
          <line
            x1={padding.left}
            y1={padding.top + plotHeight}
            x2={width - padding.right}
            y2={padding.top + plotHeight}
            stroke="#334155"
            strokeWidth="1"
          />
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={padding.top + plotHeight}
            stroke="#334155"
            strokeWidth="1"
          />

          {/* Axis Labels */}
          <text x={width / 2} y={height - 8} fill="#64748b" fontSize="10" textAnchor="middle">
            Packet Sequence Number
          </text>
        </svg>

        {history.length === 0 && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
            }}
          >
            No transmission data yet. Click &quot;Start Transmission&quot; to begin.
          </div>
        )}
      </div>
    </div>
  );
};
