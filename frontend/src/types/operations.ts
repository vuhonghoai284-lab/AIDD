/**
 * 运营数据类型定义
 */

export type TimeRangeType = '7days' | '30days' | '6months' | 'this_year' | '1year' | 'custom';

export interface OperationsTimeRange {
  type: TimeRangeType;
  start_date?: string;
  end_date?: string;
}

export interface TaskStatistics {
  total: number;
  running: number;
  completed: number;
  failed: number;
  success_rate: number;
  today_total: number;
  today_completed: number;
  today_failed: number;
}

export interface UserStatistics {
  total_users: number;
  active_users: number;
  new_registrations: number;
  today_active: number;
  today_new_registrations: number;
  current_online: number;
}

export interface IssueStatistics {
  total_issues: number;
  new_issues: number;
  accepted_issues: number;
  rejected_issues: number;
  pending_issues: number;
  critical_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
  today_new: number;
  today_accepted: number;
}

export interface FeedbackStatistics {
  total_feedback: number;
  valid_feedback: number;
  average_score: number;
  score_distribution: Record<string, number>;
  today_feedback: number;
  today_average_score: number;
}

export interface TokenConsumption {
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number;
  today_tokens: number;
  today_cost: number;
  by_model: Record<string, number>;
}

export interface CriticalIssueItem {
  id: number;
  task_id: number;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  issue_type: string;
  status: string;
  created_at: string;
  task_title: string;
}

export interface TrendDataPoint {
  date: string;
  value: number;
  new_users?: number;
  active_users?: number;
}

export interface OperationsTrends {
  task_trends: TrendDataPoint[];
  user_trends: TrendDataPoint[];
  issue_trends: TrendDataPoint[];
  token_trends: TrendDataPoint[];
}

export interface OperationsOverview {
  time_range: OperationsTimeRange;
  tasks: TaskStatistics;
  users: UserStatistics;
  issues: IssueStatistics;
  feedback: FeedbackStatistics;
  tokens: TokenConsumption;
  critical_issues: CriticalIssueItem[];
  trends: OperationsTrends;
  generated_at: string;
}

export interface OperationsRequest {
  time_range: OperationsTimeRange;
  include_trends?: boolean;
  include_critical_issues?: boolean;
  max_critical_issues?: number;
}