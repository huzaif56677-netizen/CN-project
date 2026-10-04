import React, { useState } from 'react';
import { Terminal, Trash2, ChevronDown, ChevronUp, AlertTriangle, ArrowRightLeft, CheckCircle2, Send, Clock } from 'lucide-react';

export interface LogEntry {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  level: 'info' | 'warn' | 'danger' | 'success';
}

interface EventLogProps {
  logs: LogEntry[];
  onClear: () => void;
}

export const EventLog: React.FC<EventLogProps> = ({ logs, onClear }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const getLogIcon = (type: string, level: LogEntry['level']) => {
    switch (type) {
      case 'SDN_REROUTE':
      case 'PATH_UPDATE':
        return <ArrowRightLeft size={13} color="#6366f1" />;
      case 'ALERT':
      case 'PACKET_LOST':
        return <AlertTriangle size={13} color="#f43f5e" />;
      case 'RECOVERY':
      case 'COMPLETED':
        return <CheckCircle2 size={13} color="#10b981" />;
      case 'PACKET_SENT':
        return <Send size={13} color="#3b82f6" />;
      default:
        return <Clock size={13} color="var(--text-muted)" />;
    }
  };

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'danger':
        return '#f43f5e';
      case 'warn':
        return '#f59e0b';
      case 'success':
        return '#10b981';
      default:
        return 'var(--text-secondary)';
    }
  };

  return (
    <div className="card" style={{ padding: '16px 20px', marginTop: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={16} color="var(--text-secondary)" />
          <h2 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Live Transmission & Control Event Feed
          </h2>
          <span
            style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: '9999px',
              background: 'var(--bg-surface-elevated)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {logs.length} events
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            className="btn btn-secondary"
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={onClear}
            title="Clear event logs"
          >
            <Trash2 size={13} /> Clear
          </button>
          <button
            className="btn btn-secondary"
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div
          style={{
            marginTop: '12px',
            maxHeight: '220px',
            overflowY: 'auto',
            background: 'var(--bg-surface-subtle)',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            padding: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            fontSize: '0.78rem',
          }}
        >
          {logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
              No events logged yet. Events will appear as packets are transmitted.
            </div>
          ) : (
            logs.slice(-60).reverse().map((log) => (
              <div
                key={log.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  background: 'rgba(255, 255, 255, 0.015)',
                  borderLeft: `2px solid ${getLevelColor(log.level)}`,
                }}
              >
                <span className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.72rem', flexShrink: 0 }}>
                  {log.timestamp}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                  {getLogIcon(log.type, log.level)}
                </span>
                <span style={{ color: 'var(--text-primary)', flex: 1, wordBreak: 'break-word' }}>
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
