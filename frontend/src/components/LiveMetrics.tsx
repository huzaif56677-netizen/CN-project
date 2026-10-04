import React from 'react';
import { Send, CheckCircle2, TrendingDown, Clock, Repeat } from 'lucide-react';
import { ExperimentState } from '../types';

interface MetricsProps {
  state: ExperimentState;
}

export const LiveMetrics: React.FC<MetricsProps> = ({ state }) => {
  const isThresholdBreached = state.current_loss_rate >= state.threshold;
  const progressPct = Math.min(100, Math.round((state.current_seq / 100) * 100));

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '20px' }}>
      {/* 1. Transmission Progress */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Packets Sent
          </span>
          <Send size={16} color="#3b82f6" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
          <span className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {state.current_seq}
          </span>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ 100</span>
        </div>
        {/* Simple Progress Bar */}
        <div style={{ width: '100%', height: '5px', background: 'var(--bg-surface-elevated)', borderRadius: '3px', marginTop: '10px', overflow: 'hidden' }}>
          <div style={{ width: `${progressPct}%`, height: '100%', background: '#3b82f6', transition: 'width 0.2s ease' }} />
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
          Current Sequence: #{state.current_seq}
        </div>
      </div>

      {/* 2. ACKs vs Drops */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Delivery Success & Drops
          </span>
          <CheckCircle2 size={16} color="#10b981" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
          <div>
            <span className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: '#10b981' }}>
              {state.total_received}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '4px' }}>ACKs</span>
          </div>
          <span style={{ color: 'var(--border-hover)' }}>/</span>
          <div>
            <span className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: state.total_lost > 0 ? '#f43f5e' : 'var(--text-muted)' }}>
              {state.total_lost}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '4px' }}>Lost</span>
          </div>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Repeat size={12} /> {state.total_retransmissions} retransmission requests sent
        </div>
      </div>

      {/* 3. Measured Loss Rate */}
      <div
        className="card"
        style={{
          padding: '16px',
          borderLeft: state.total_lost > 0 ? '3px solid #f43f5e' : '3px solid #10b981',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Real-Time Packet Loss
          </span>
          <TrendingDown size={16} color={state.total_lost > 0 ? '#f43f5e' : '#10b981'} />
        </div>
        <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: state.total_lost > 0 ? '#f43f5e' : '#10b981' }}>
          {state.current_loss_rate.toFixed(1)}%
        </div>
        <div style={{ fontSize: '0.75rem', marginTop: '10px', color: state.total_lost > 0 ? '#fb7185' : 'var(--text-muted)' }}>
          {state.total_lost > 0 ? (
            <span style={{ fontWeight: 600 }}>Loss Detected: {state.total_lost} dropped</span>
          ) : (
            <span>0 Packet Loss (Healthy)</span>
          )}
        </div>
      </div>

      {/* 4. Measured Recovery Time */}
      <div
        className="card"
        style={{
          padding: '16px',
          borderLeft: state.recovery_time_ms ? '3px solid #10b981' : '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            SDN Failover Recovery Time
          </span>
          <Clock size={16} color={state.recovery_time_ms ? '#10b981' : '#64748b'} />
        </div>
        <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: state.recovery_time_ms ? '#10b981' : 'var(--text-muted)' }}>
          {state.recovery_time_ms ? `${state.recovery_time_ms.toFixed(1)} ms` : '—'}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '10px' }}>
          {state.recovery_time_ms
            ? 'Measured from T1 (trigger) to T2 (first ACK)'
            : 'Awaiting loss trigger to measure failover'}
        </div>
      </div>
    </div>
  );
};
