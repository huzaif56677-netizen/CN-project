import React from 'react';
import { Send, AlertTriangle, ArrowRightLeft, CheckCircle2 } from 'lucide-react';
import { ExperimentState } from '../types';

interface ProgressProps {
  state: ExperimentState;
}

export const ExperimentProgress: React.FC<ProgressProps> = ({ state }) => {
  const isStarted = state.status !== 'IDLE';
  const isLossDetected = state.total_lost > 0 || state.reroute_triggered;
  const isRerouted = state.reroute_triggered || state.active_path === 'alternate_s3';
  const isRecovered = state.status === 'RECOVERED' || state.status === 'COMPLETED' || state.recovery_time_ms !== null;

  const steps = [
    {
      id: 1,
      title: '1. Primary Path',
      desc: 'Transmitting UDP packets via s1 ➔ s2 ➔ s4',
      icon: Send,
      active: isStarted && !isLossDetected,
      completed: isLossDetected,
      accentColor: '#3b82f6',
    },
    {
      id: 2,
      title: '2. Packet Loss Detected',
      desc: isLossDetected
        ? `${state.total_lost} unacknowledged packet drop(s) detected on wire`
        : 'Actively monitoring for missing packets / timeouts',
      icon: AlertTriangle,
      active: isLossDetected && !isRerouted,
      completed: isRerouted,
      accentColor: '#f59e0b',
    },
    {
      id: 3,
      title: '3. Dynamic SDN Reroute',
      desc: 'Ryu updates OpenFlow rules to divert traffic to clean switch s3',
      icon: ArrowRightLeft,
      active: isRerouted && !isRecovered,
      completed: isRecovered,
      accentColor: '#6366f1',
    },
    {
      id: 4,
      title: '4. Traffic Recovered',
      desc: state.recovery_time_ms
        ? `Recovered in ${state.recovery_time_ms.toFixed(1)} ms (Zero loss restored)`
        : 'Packet delivery restored over alternate path',
      icon: CheckCircle2,
      active: isRecovered,
      completed: state.status === 'COMPLETED',
      accentColor: '#10b981',
    },
  ];

  return (
    <div className="card" style={{ padding: '16px 20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Real-Time Network Lifecycle
        </span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {state.status === 'IDLE' && 'Waiting for transmission to start'}
          {state.status === 'RUNNING' && !isLossDetected && 'Transmitting on Primary Path (Clean so far)'}
          {state.status === 'RUNNING' && isLossDetected && !isRerouted && 'Real packet loss detected! Rerouting...'}
          {state.status === 'RUNNING' && isRerouted && 'Traffic diverted to alternate path s3'}
          {state.status === 'RECOVERED' && 'Traffic successfully recovered'}
          {state.status === 'COMPLETED' && 'All 100 packets transmitted'}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
        {steps.map((step) => {
          const Icon = step.icon;
          const isCurrent = step.active;
          const isDone = step.completed;

          let bg = 'rgba(255, 255, 255, 0.02)';
          let border = 'var(--border-subtle)';
          let iconColor = 'var(--text-muted)';
          let titleColor = 'var(--text-secondary)';

          if (isCurrent) {
            bg = 'rgba(59, 130, 246, 0.08)';
            border = step.accentColor;
            iconColor = step.accentColor;
            titleColor = 'var(--text-primary)';
          } else if (isDone) {
            bg = 'rgba(16, 185, 129, 0.05)';
            border = 'rgba(16, 185, 129, 0.3)';
            iconColor = '#10b981';
            titleColor = 'var(--text-primary)';
          }

          return (
            <div
              key={step.id}
              style={{
                background: bg,
                border: `1px solid ${border}`,
                borderRadius: '8px',
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                transition: 'all 0.2s ease',
              }}
            >
              <div
                style={{
                  background: isCurrent
                    ? 'rgba(59, 130, 246, 0.15)'
                    : isDone
                    ? 'rgba(16, 185, 129, 0.15)'
                    : 'rgba(255, 255, 255, 0.05)',
                  padding: '8px',
                  borderRadius: '6px',
                  color: iconColor,
                  display: 'flex',
                  marginTop: '2px',
                }}
              >
                <Icon size={18} />
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: titleColor }}>
                  {step.title}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px', lineHeight: 1.3 }}>
                  {step.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
