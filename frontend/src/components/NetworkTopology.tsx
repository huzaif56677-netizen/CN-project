import React from 'react';
import { Cpu, Server, Monitor, ShieldCheck, AlertCircle } from 'lucide-react';
import { ExperimentState } from '../types';

interface TopologyProps {
  state: ExperimentState;
}

export const NetworkTopology: React.FC<TopologyProps> = ({ state }) => {
  const isAlternate = state.active_path === 'alternate_s3';
  const isRunning = state.status === 'RUNNING';

  return (
    <div className="card" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Mininet Diamond Network Topology
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            OpenFlow 1.3 data plane with 2 physical paths between h1 and h2
          </p>
        </div>

        <div
          style={{
            fontSize: '0.75rem',
            padding: '4px 10px',
            borderRadius: '6px',
            background: isAlternate ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            color: isAlternate ? '#10b981' : '#f43f5e',
            border: `1px solid ${isAlternate ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
            fontWeight: 600,
          }}
        >
          {isAlternate ? 'Active: Alternate Path (s3)' : 'Active: Primary Path (s2)'}
        </div>
      </div>

      <div
        style={{
          flex: 1,
          position: 'relative',
          minHeight: '280px',
          background: 'var(--bg-surface-subtle)',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '10px',
        }}
      >
        <svg viewBox="0 0 720 280" style={{ width: '100%', height: '100%', maxHeight: '340px' }}>
          {/* OpenFlow Control Plane Lines (Ryu Controller to Switches) */}
          <line x1="360" y1="38" x2="220" y2="140" stroke="#475569" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />
          <line x1="360" y1="38" x2="360" y2="85" stroke="#475569" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />
          <line x1="360" y1="38" x2="360" y2="195" stroke="#475569" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />
          <line x1="360" y1="38" x2="500" y2="140" stroke="#475569" strokeDasharray="3,3" strokeWidth="1" opacity="0.6" />

          {/* Physical Data Links */}
          {/* h1 <-> s1 */}
          <line
            x1="80"
            y1="140"
            x2="220"
            y2="140"
            stroke={isRunning ? '#3b82f6' : '#334155'}
            strokeWidth="3"
            className={isRunning ? 'active-path-clean' : ''}
          />

          {/* s1 <-> s2 (Primary Path - 20% lossy) */}
          <line
            x1="220"
            y1="140"
            x2="360"
            y2="85"
            stroke={!isAlternate && isRunning ? '#f43f5e' : '#334155'}
            strokeWidth={!isAlternate ? '4' : '2'}
            strokeOpacity={isAlternate ? 0.3 : 1}
            className={!isAlternate && isRunning ? 'active-path-lossy' : ''}
          />

          {/* s2 <-> s4 (Primary Path) */}
          <line
            x1="360"
            y1="85"
            x2="500"
            y2="140"
            stroke={!isAlternate && isRunning ? '#f59e0b' : '#334155'}
            strokeWidth={!isAlternate ? '4' : '2'}
            strokeOpacity={isAlternate ? 0.3 : 1}
            className={!isAlternate && isRunning ? 'active-path-lossy' : ''}
          />

          {/* s1 <-> s3 (Alternate Path - 0% loss) */}
          <line
            x1="220"
            y1="140"
            x2="360"
            y2="195"
            stroke={isAlternate && isRunning ? '#10b981' : '#334155'}
            strokeWidth={isAlternate ? '4' : '2'}
            strokeOpacity={!isAlternate ? 0.35 : 1}
            className={isAlternate && isRunning ? 'active-path-clean' : ''}
          />

          {/* s3 <-> s4 (Alternate Path) */}
          <line
            x1="360"
            y1="195"
            x2="500"
            y2="140"
            stroke={isAlternate && isRunning ? '#10b981' : '#334155'}
            strokeWidth={isAlternate ? '4' : '2'}
            strokeOpacity={!isAlternate ? 0.35 : 1}
            className={isAlternate && isRunning ? 'active-path-clean' : ''}
          />

          {/* s4 <-> h2 */}
          <line
            x1="500"
            y1="140"
            x2="640"
            y2="140"
            stroke={isRunning ? (isAlternate ? '#10b981' : '#f59e0b') : '#334155'}
            strokeWidth="3"
            className={isRunning ? 'active-path-clean' : ''}
          />

          {/* Ryu Controller Node */}
          <g transform="translate(360, 32)">
            <rect x="-70" y="-16" width="140" height="32" rx="6" fill="#1e293b" stroke="#6366f1" strokeWidth="1.5" />
            <text x="0" y="4" fill="#cbd5e1" fontSize="11" fontWeight="600" textAnchor="middle">
              Ryu SDN Controller
            </text>
          </g>

          {/* Host h1 (Sender) */}
          <g transform="translate(80, 140)">
            <circle r="24" fill="#1e293b" stroke="#3b82f6" strokeWidth="2" />
            <text x="0" y="-4" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">h1</text>
            <text x="0" y="10" fill="#94a3b8" fontSize="9" textAnchor="middle">Sender</text>
            <text x="0" y="38" fill="#64748b" fontSize="10" textAnchor="middle" className="mono">10.0.0.1</text>
          </g>

          {/* Switch s1 */}
          <g transform="translate(220, 140)">
            <rect x="-24" y="-24" width="48" height="48" rx="6" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
            <text x="0" y="4" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">s1</text>
            <text x="0" y="38" fill="#64748b" fontSize="10" textAnchor="middle">Ingress</text>
          </g>

          {/* Switch s2 (Top - Primary Path) */}
          <g transform="translate(360, 85)">
            <rect
              x="-50"
              y="-22"
              width="100"
              height="44"
              rx="6"
              fill="#1e293b"
              stroke={state.total_lost > 0 ? '#f43f5e' : (!isAlternate ? '#3b82f6' : '#475569')}
              strokeWidth={!isAlternate ? '2' : '1'}
            />
            <text x="0" y="-3" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">s2 (Primary)</text>
            <text
              x="0"
              y="12"
              fill={state.total_lost > 0 ? '#fb7185' : (!isAlternate ? '#60a5fa' : '#64748b')}
              fontSize="9.5"
              fontWeight="600"
              textAnchor="middle"
            >
              {state.total_lost > 0 ? 'Loss Detected!' : (!isAlternate ? 'Active (Monitoring)' : 'Bypassed')}
            </text>
          </g>

          {/* Switch s3 (Bottom - Alternate Path) */}
          <g transform="translate(360, 195)">
            <rect
              x="-50"
              y="-22"
              width="100"
              height="44"
              rx="6"
              fill="#1e293b"
              stroke={isAlternate ? '#10b981' : '#475569'}
              strokeWidth={isAlternate ? '2' : '1'}
            />
            <text x="0" y="-3" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">s3 (Alternate)</text>
            <text x="0" y="12" fill={isAlternate ? '#34d399' : '#64748b'} fontSize="9.5" fontWeight="600" textAnchor="middle">
              {isAlternate ? 'Active (Clean)' : 'Standby Path'}
            </text>
          </g>

          {/* Switch s4 */}
          <g transform="translate(500, 140)">
            <rect x="-24" y="-24" width="48" height="48" rx="6" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
            <text x="0" y="4" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">s4</text>
            <text x="0" y="38" fill="#64748b" fontSize="10" textAnchor="middle">Egress</text>
          </g>

          {/* Host h2 (Receiver) */}
          <g transform="translate(640, 140)">
            <circle r="24" fill="#1e293b" stroke="#10b981" strokeWidth="2" />
            <text x="0" y="-4" fill="#f8fafc" fontSize="12" fontWeight="700" textAnchor="middle">h2</text>
            <text x="0" y="10" fill="#94a3b8" fontSize="9" textAnchor="middle">Receiver</text>
            <text x="0" y="38" fill="#64748b" fontSize="10" textAnchor="middle" className="mono">10.0.0.2</text>
          </g>
        </svg>
      </div>

      <div
        style={{
          marginTop: '12px',
          padding: '10px 14px',
          background: 'var(--bg-surface-elevated)',
          borderRadius: '6px',
          fontSize: '0.78rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {!isAlternate ? (
          <>
            <AlertCircle size={15} color="#3b82f6" />
            <span>
              <strong>Primary Path active:</strong> Packets traverse <code>s1 ➔ s2 ➔ s4</code>. The system continuously listens for packet loss via socket timeouts and missing sequence gaps. If any loss is detected, Ryu will dynamically divert traffic to <code>s3</code>.
            </span>
          </>
        ) : (
          <>
            <ShieldCheck size={15} color="#10b981" />
            <span>
              <strong>SDN Reroute completed:</strong> Packet loss was detected on the primary path! Ryu installed OpenFlow rules to bypass <code>s2</code>. Traffic now flows through <code>s1 ➔ s3 ➔ s4</code>.
            </span>
          </>
        )}
      </div>
    </div>
  );
};
