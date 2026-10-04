import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { ExperimentProgress } from './components/ExperimentProgress';
import { NetworkTopology } from './components/NetworkTopology';
import { LiveMetrics } from './components/LiveMetrics';
import { LossChart } from './components/LossChart';
import { ComparisonTable } from './components/ComparisonTable';
import { EventLog, LogEntry } from './components/EventLog';
import { ExperimentState, WebSocketMessage } from './types';

const INITIAL_STATE: ExperimentState = {
  status: 'IDLE',
  active_path: 'primary_s2',
  current_seq: 0,
  total_sent: 0,
  total_received: 0,
  total_lost: 0,
  total_retransmissions: 0,
  current_loss_rate: 0.0,
  threshold: 15.0,
  t1_trigger: null,
  t2_recovery: null,
  recovery_time_ms: null,
  reroute_triggered: false,
  loss_history: [],
  before_stats: {
    active_path: 's1 -> s2 -> s4',
    packets_sent: 0,
    packets_lost: 0,
    loss_rate: 0.0,
    retransmissions: 0,
  },
  after_stats: {
    active_path: 's1 -> s3 -> s4',
    packets_sent: 0,
    packets_lost: 0,
    loss_rate: 0.0,
    retransmissions: 0,
  },
};

const BACKEND_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

export const App: React.FC = () => {
  const [state, setState] = useState<ExperimentState>(INITIAL_STATE);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const addLog = (type: string, message: string, level: LogEntry['level'] = 'info') => {
    const now = new Date().toTimeString().slice(0, 8);
    const id = Math.random().toString(36).substring(2, 9);
    setLogs((prev) => [...prev.slice(-150), { id, type, message, timestamp: now, level }]);
  };

  // Connect to WebSocket
  useEffect(() => {
    let reconnectTimeout: any;
    let isMounted = true;
    let wsInstance: WebSocket | null = null;

    const connectWebSocket = () => {
      if (!isMounted) return;
      const ws = new WebSocket(WS_URL);
      wsInstance = ws;
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) {
          ws.close();
          return;
        }
        setIsConnected(true);
        addLog('SYSTEM', 'Connected to Mininet & SDN Event Stream', 'success');
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setIsConnected(false);
        addLog('SYSTEM', 'Disconnected from Event Stream. Reconnecting...', 'warn');
        reconnectTimeout = setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = () => {
        if (!isMounted) return;
        setIsConnected(false);
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);
          handleIncomingEvent(msg);
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (wsInstance) {
        wsInstance.close();
      }
      wsRef.current = null;
    };
  }, []);

  const handleIncomingEvent = (msg: WebSocketMessage) => {
    const { type, data, server_state } = msg;

    // Direct synchronization with authoritative backend state
    if (server_state) {
      setState(server_state);
    } else if (type === 'INIT_STATE') {
      setState(data);
      return;
    }

    if (type === 'PACKET_SENT') {
      if (!server_state) {
        setState((prev) => {
          const nextBeforeSent = data.phase === 'before' ? prev.before_stats.packets_sent + 1 : prev.before_stats.packets_sent;
          const nextAfterSent = data.phase === 'after' ? prev.after_stats.packets_sent + 1 : prev.after_stats.packets_sent;
          return {
            ...prev,
            status: prev.status === 'IDLE' ? 'RUNNING' : prev.status,
            current_seq: data.seq,
            total_sent: prev.total_sent + 1,
            before_stats: {
              ...prev.before_stats,
              packets_sent: nextBeforeSent,
              loss_rate: nextBeforeSent > 0 ? Number(((prev.before_stats.packets_lost / nextBeforeSent) * 100).toFixed(1)) : 0,
            },
            after_stats: {
              ...prev.after_stats,
              packets_sent: nextAfterSent,
              loss_rate: nextAfterSent > 0 ? Number(((prev.after_stats.packets_lost / nextAfterSent) * 100).toFixed(1)) : 0,
            },
          };
        });
      }

      if (data.seq % 10 === 0 || data.seq === 1) {
        addLog('PACKET_SENT', `Packet #${data.seq} sent via ${data.phase === 'after' ? 'Alternate (s3)' : 'Primary (s2)'}`);
      }
    } else if (type === 'ACK_RECEIVED') {
      if (!server_state) {
        setState((prev) => ({
          ...prev,
          total_received: prev.total_received + 1,
        }));
      }
    } else if (type === 'PACKET_LOST') {
      // This event fires exactly once per packet (after all retries exhausted)
      if (!server_state) {
        setState((prev) => {
          const nextBeforeLost = data.phase === 'before' ? prev.before_stats.packets_lost + 1 : prev.before_stats.packets_lost;
          const nextAfterLost = data.phase === 'after' ? prev.after_stats.packets_lost + 1 : prev.after_stats.packets_lost;
          return {
            ...prev,
            total_lost: prev.total_lost + 1,
            before_stats: {
              ...prev.before_stats,
              packets_lost: nextBeforeLost,
              loss_rate: prev.before_stats.packets_sent > 0 ? Number(((nextBeforeLost / prev.before_stats.packets_sent) * 100).toFixed(1)) : 0,
            },
            after_stats: {
              ...prev.after_stats,
              packets_lost: nextAfterLost,
              loss_rate: prev.after_stats.packets_sent > 0 ? Number(((nextAfterLost / prev.after_stats.packets_sent) * 100).toFixed(1)) : 0,
            },
          };
        });
      }
      addLog('PACKET_LOST', `Packet #${data.seq} lost after ${data.attempts_made} attempt(s) on ${data.phase === 'after' ? 'Alternate link' : 'Primary link'}`, 'danger');
    } else if (type === 'TIMEOUT') {
      // Per-attempt timeout - log only, no counting
      addLog('TIMEOUT', `Timeout: Packet #${data.seq} (attempt ${data.attempt}/${data.max_attempts}) on ${data.phase === 'after' ? 'Alternate link' : 'Primary link'}`, 'warn');
    } else if (type === 'RETRANSMISSION') {
      if (!server_state) {
        setState((prev) => ({
          ...prev,
          total_retransmissions: prev.total_retransmissions + 1,
          before_stats:
            data.phase === 'before'
              ? { ...prev.before_stats, retransmissions: prev.before_stats.retransmissions + 1 }
              : prev.before_stats,
          after_stats:
            data.phase === 'after'
              ? { ...prev.after_stats, retransmissions: prev.after_stats.retransmissions + 1 }
              : prev.after_stats,
        }));
      }
      addLog('RETRANSMIT', `Retrying Packet #${data.seq} (Attempt ${data.attempt})`, 'warn');
    } else if (type === 'LOSS_UPDATE') {
      setState((prev) => ({
        ...prev,
        current_loss_rate: data.window_loss_rate,
        loss_history: [
          ...prev.loss_history.slice(-100),
          {
            seq: data.seq,
            loss_rate: data.window_loss_rate,
            threshold: data.threshold,
            path: data.path,
          },
        ],
      }));
    } else if (type === 'THRESHOLD_EXCEEDED') {
      setState((prev) => ({
        ...prev,
        t1_trigger: data.t1,
        reroute_triggered: true,
      }));
      addLog('ALERT', `Loss threshold exceeded! Triggering SDN dynamic reroute!`, 'danger');
    } else if (type === 'REROUTE_STARTED') {
      setState((prev) => ({
        ...prev,
        active_path: 'alternate_s3',
      }));
      addLog('SDN_REROUTE', 'Ryu pushed OpenFlow rules: Traffic diverted to alternate path s1 ➔ s3 ➔ s4', 'success');
    } else if (type === 'PATH_CHANGED') {
      setState((prev) => ({
        ...prev,
        active_path: data.active_path,
      }));
      addLog('PATH_UPDATE', `Active route changed to ${data.active_path}`, 'info');
    } else if (type === 'RECOVERY_COMPLETED') {
      setState((prev) => ({
        ...prev,
        status: 'RECOVERED',
        t2_recovery: data.t2,
        recovery_time_ms: data.recovery_time_ms,
      }));
      addLog('RECOVERY', `Traffic recovered on Alternate Path in ${data.recovery_time_ms} ms!`, 'success');
    } else if (type === 'EXPERIMENT_COMPLETED') {
      // Use the authoritative final stats from the UDP client
      setState((prev) => {
        const beforeSent = data.before?.packets_sent ?? prev.before_stats.packets_sent;
        const beforeLost = data.before?.packets_lost ?? prev.before_stats.packets_lost;
        const afterSent = data.after?.packets_sent ?? prev.after_stats.packets_sent;
        const afterLost = data.after?.packets_lost ?? prev.after_stats.packets_lost;

        return {
          ...prev,
          status: 'COMPLETED',
          total_sent: data.total_sent ?? prev.total_sent,
          total_received: data.total_received ?? prev.total_received,
          total_lost: data.total_lost ?? prev.total_lost,
          total_retransmissions: data.total_retransmissions ?? prev.total_retransmissions,
          recovery_time_ms: data.recovery_time_ms ?? prev.recovery_time_ms,
          reroute_triggered: data.reroute_triggered ?? prev.reroute_triggered,
          before_stats: {
            ...prev.before_stats,
            packets_sent: beforeSent,
            packets_lost: beforeLost,
            retransmissions: data.before?.retransmissions ?? prev.before_stats.retransmissions,
            loss_rate: data.before?.loss_rate ?? (beforeSent > 0 ? Math.round((beforeLost / beforeSent) * 10000) / 100 : 0),
          },
          after_stats: {
            ...prev.after_stats,
            packets_sent: afterSent,
            packets_lost: afterLost,
            retransmissions: data.after?.retransmissions ?? prev.after_stats.retransmissions,
            loss_rate: data.after?.loss_rate ?? (afterSent > 0 ? Math.round((afterLost / afterSent) * 10000) / 100 : 0),
          },
        };
      });
      addLog('COMPLETED', 'UDP transmission complete. All empirical statistics recorded.', 'success');
    } else if (type === 'EXPERIMENT_RESET') {
      setState(INITIAL_STATE);
      addLog('RESET', 'Experiment metrics and Ryu OpenFlow rules reset.', 'info');
    }
  };

  const handleStart = async () => {
    try {
      await fetch(`${BACKEND_BASE}/api/experiment/start`, { method: 'POST' });
      addLog('CONTROL', 'Starting transmission: Spawning UDP client...', 'info');
    } catch (err: any) {
      addLog('ERROR', `Failed to start transmission: ${err.message}`, 'danger');
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${BACKEND_BASE}/api/experiment/stop`, { method: 'POST' });
      addLog('CONTROL', 'Transmission stopped by user.', 'warn');
    } catch (err: any) {
      addLog('ERROR', `Failed to stop transmission: ${err.message}`, 'danger');
    }
  };

  const handleReset = async () => {
    try {
      await fetch(`${BACKEND_BASE}/api/reset`, { method: 'POST' });
      setState(INITIAL_STATE);
      addLog('CONTROL', 'Reset command sent to backend and Ryu controller.', 'info');
    } catch (err: any) {
      addLog('ERROR', `Failed to reset: ${err.message}`, 'danger');
    }
  };

  const handleManualReroute = async () => {
    try {
      await fetch(`${BACKEND_BASE}/api/reroute`, { method: 'POST' });
      addLog('CONTROL', 'Manual reroute command sent to Ryu controller.', 'warn');
    } catch (err: any) {
      addLog('ERROR', `Failed manual reroute: ${err.message}`, 'danger');
    }
  };

  return (
    <div style={{ maxWidth: '1360px', margin: '0 auto', padding: '24px 20px' }}>
      <Header
        state={state}
        isConnected={isConnected}
        onStart={handleStart}
        onStop={handleStop}
        onReset={handleReset}
        onManualReroute={handleManualReroute}
      />

      <ExperimentProgress state={state} />

      <LiveMetrics state={state} />

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', alignItems: 'stretch' }}>
        <NetworkTopology state={state} />
        <LossChart state={state} />
      </div>

      <ComparisonTable state={state} />

      <EventLog logs={logs} onClear={() => setLogs([])} />
    </div>
  );
};

export default App;
