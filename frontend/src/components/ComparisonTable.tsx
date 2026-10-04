import React from 'react';
import { ArrowRight, Check, AlertTriangle, Clock, ShieldCheck } from 'lucide-react';
import { ExperimentState } from '../types';

interface ComparisonProps {
  state: ExperimentState;
}

export const ComparisonTable: React.FC<ComparisonProps> = ({ state }) => {
  const before = state.before_stats;
  const after = state.after_stats;

  const beforeLossRate = before.packets_sent > 0
    ? (before.packets_lost / before.packets_sent) * 100
    : (before.loss_rate || 0);

  const afterLossRate = after.packets_sent > 0
    ? (after.packets_lost / after.packets_sent) * 100
    : (after.loss_rate || 0);

  return (
    <div className="card" style={{ padding: '20px', marginTop: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Empirical Results: Before vs. After SDN Reroute
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Direct comparison of network performance across degraded primary vs. alternate path
          </p>
        </div>

        {state.recovery_time_ms !== null && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              borderRadius: '8px',
              color: '#34d399',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}
          >
            <Clock size={15} />
            <span>Failover Recovery Time: {state.recovery_time_ms.toFixed(2)} ms</span>
          </div>
        )}
      </div>

      {/* Side-by-Side Comparison Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '16px' }}>
        {/* Phase 1: Primary Path */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderLeft: '4px solid #f43f5e',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f43f5e', textTransform: 'uppercase' }}>
              Phase 1: Before Reroute (Primary)
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="mono">
              s1 ➔ s2 ➔ s4
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Packet Loss Rate</div>
              <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f43f5e', marginTop: '2px' }}>
                {beforeLossRate.toFixed(1)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Packets Lost</div>
              <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                {before.packets_lost} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/ {before.packets_sent}</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Path Health</div>
              <div style={{ fontSize: '0.85rem', color: before.packets_lost > 0 ? '#f43f5e' : 'var(--text-secondary)', marginTop: '2px', fontWeight: 600 }}>
                {before.packets_lost > 0 ? 'Degraded Link' : 'Normal'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Retransmissions</div>
              <div className="mono" style={{ fontSize: '0.85rem', color: '#f59e0b', marginTop: '2px', fontWeight: 600 }}>
                {before.retransmissions} retries
              </div>
            </div>
          </div>
        </div>

        {/* Phase 2: Alternate Path */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderLeft: '4px solid #10b981',
            borderRadius: '8px',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', textTransform: 'uppercase' }}>
              Phase 2: After Reroute (Alternate)
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="mono">
              s1 ➔ s3 ➔ s4
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Packet Loss Rate</div>
              <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                {afterLossRate.toFixed(1)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Packets Lost</div>
              <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                {after.packets_lost} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/ {after.packets_sent}</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Path Health</div>
              <div style={{ fontSize: '0.85rem', color: after.packets_lost === 0 ? '#10b981' : '#f59e0b', marginTop: '2px', fontWeight: 600 }}>
                {after.packets_lost === 0 ? 'Clean Alternate Link' : `Partial Loss (${afterLossRate.toFixed(1)}%)`}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Retransmissions</div>
              <div className="mono" style={{ fontSize: '0.85rem', color: after.retransmissions > 0 ? '#f59e0b' : '#10b981', marginTop: '2px', fontWeight: 600 }}>
                {after.retransmissions} retries
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Note */}
      <div
        style={{
          padding: '12px 14px',
          background: 'var(--bg-surface-elevated)',
          borderRadius: '6px',
          fontSize: '0.78rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <ShieldCheck size={16} color="#10b981" />
        <span>
          <strong>Key Result:</strong> When real packet loss was detected on the primary path, Ryu immediately switched traffic to alternate switch <code>s3</code> in{' '}
          <strong style={{ color: '#10b981' }}>
            {state.recovery_time_ms ? `${state.recovery_time_ms.toFixed(1)} ms` : '—'}
          </strong>
          {state.status === 'COMPLETED' ? (
            <>
              {', restoring packet delivery with '}
              <strong style={{ color: afterLossRate === 0 ? '#10b981' : '#f59e0b' }}>
                {afterLossRate.toFixed(1)}%
              </strong>
              {afterLossRate === 0 ? ' loss on alternate path (100% reliable).' : ' loss on alternate path.'}
            </>
          ) : (
            ', restoring reliable packet delivery on the alternate path.'
          )}
        </span>
      </div>
    </div>
  );
};
