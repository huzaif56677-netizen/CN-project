import React from 'react';
import { Network, Play, Square, RefreshCw, ArrowRightLeft } from 'lucide-react';
import { ExperimentState } from '../types';

interface HeaderProps {
  state: ExperimentState;
  isConnected: boolean;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onManualReroute: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  state,
  isConnected,
  onStart,
  onStop,
  onReset,
  onManualReroute,
}) => {
  const getStatusBadge = () => {
    switch (state.status) {
      case 'RUNNING':
        return (
          <span className="badge badge-running">
            <span className="pulse-dot"></span> Transmitting
          </span>
        );
      case 'RECOVERED':
        return <span className="badge badge-recovered">Recovered (Alternate s3)</span>;
      case 'COMPLETED':
        return <span className="badge badge-recovered">Completed (100 Packets)</span>;
      case 'STOPPED':
        return <span className="badge badge-danger">Stopped</span>;
      default:
        return <span className="badge badge-idle">Ready to Run</span>;
    }
  };

  const isAlternate = state.active_path === 'alternate_s3';

  return (
    <header
      className="card"
      style={{
        padding: '16px 20px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.12)',
            color: '#3b82f6',
            padding: '10px',
            borderRadius: '10px',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            display: 'flex',
          }}
        >
          <Network size={22} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              SDN Packet Loss Detection & Dynamic Rerouting
            </h1>
            {getStatusBadge()}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Mininet Diamond Topology &bull; Ryu OpenFlow 1.3 &bull; Real-Time UDP Sequence Tracking
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        {/* Backend connectivity indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: isConnected ? '#10b981' : '#f43f5e',
            padding: '6px 12px',
            background: 'var(--bg-surface-elevated)',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: isConnected ? '#10b981' : '#f43f5e',
            }}
          />
          {isConnected ? 'Backend Connected' : 'Backend Disconnected'}
        </div>

        {/* Experiment Actions */}
        {state.status !== 'RUNNING' ? (
          <button className="btn btn-primary" onClick={onStart} disabled={!isConnected}>
            <Play size={15} /> Start Transmission
          </button>
        ) : (
          <button className="btn btn-danger" onClick={onStop}>
            <Square size={15} /> Stop
          </button>
        )}

        <button
          className="btn btn-secondary"
          onClick={onManualReroute}
          disabled={isAlternate || state.status !== 'RUNNING'}
          title="Manually instruct Ryu controller to divert traffic to s3"
        >
          <ArrowRightLeft size={14} /> Force Reroute
        </button>

        <button className="btn btn-secondary" onClick={onReset} title="Reset experiment metrics and OpenFlow rules">
          <RefreshCw size={14} /> Reset
        </button>
      </div>
    </header>
  );
};
