export interface PhaseStats {
  active_path: string;
  packets_sent: number;
  packets_lost: number;
  loss_rate: number;
  retransmissions: number;
}

export interface LossPoint {
  seq: number;
  loss_rate: number;
  threshold: number;
  path: string;
}

export interface ExperimentState {
  status: 'IDLE' | 'STARTING' | 'RUNNING' | 'RECOVERED' | 'COMPLETED' | 'STOPPED';
  active_path: 'primary_s2' | 'alternate_s3';
  current_seq: number;
  total_sent: number;
  total_received: number;
  total_lost: number;
  total_retransmissions: number;
  current_loss_rate: number;
  threshold: number;
  t1_trigger: number | null;
  t2_recovery: number | null;
  recovery_time_ms: number | null;
  reroute_triggered: boolean;
  loss_history: LossPoint[];
  before_stats: PhaseStats;
  after_stats: PhaseStats;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  server_state?: ExperimentState;
  timestamp?: number;
}
