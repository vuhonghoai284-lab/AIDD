// 类型定义
export interface Task {
  id: number;
  title: string;
  file_name: string;
  file_size?: number;
  file_type?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  issue_count?: number;  // 新增：问题数量
  processed_issues?: number; // 新增：已处理问题数量
  ai_model_label?: string;   // 新增：模型名称
  document_chars?: number; // 新增：文档字符数
  processing_time?: number; // 新增：处理耗时(秒)
  created_at: string;
  completed_at?: string;
  error_message?: string;
  created_by?: string; // 新增：创建人ID
  created_by_name?: string; // 新增：创建人名称
  created_by_type?: string; // 新增：创建人类型
  user_id?: number; // 新增：用户ID
  file_id?: number; // 新增：文件ID
  ai_model_id?: number; // 新增：AI模型ID
}

// 分页参数
export interface PaginationParams {
  page: number;
  page_size: number;
  search?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface Issue {
  id: number;
  issue_type: string;
  description: string;
  location: string;
  severity: string;
  confidence?: number;        // 新增：模型置信度 (0.0-1.0)
  suggestion: string;
  original_text?: string;    // 新增：原文内容
  user_impact?: string;       // 新增：对用户的影响
  reasoning?: string;         // 新增：判定原因
  context?: string;           // 新增：上下文
  feedback_type?: 'accept' | 'reject';
  feedback_comment?: string;
}

export interface IssueSummary {
  total: number;
  processed: number;
  unprocessed: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  by_feedback: {
    processed: number;
    unprocessed: number;
    accept: number;
    reject: number;
  };
}

export interface AIOutputSummary {
  total: number;
  successful: number;
  failed: number;
}

export interface TaskDetail {
  task: Task;
  issues: Issue[];
  issue_summary?: IssueSummary;
  ai_output_summary?: AIOutputSummary;
}

export interface AIOutput {
  id: number;
  task_id: number;
  operation_type: string;
  section_title?: string;
  section_index?: number;
  input_text: string;
  raw_output: string;
  parsed_output?: any;
  status: string;
  error_message?: string;
  tokens_used?: number;
  processing_time?: number;
  created_at: string;
}

export interface User {
  id: number;
  uid: string;
  display_name?: string;
  email?: string;
  avatar_url?: string;
  is_admin: boolean;
  is_system_admin: boolean;
  created_at: string;
  last_login_at?: string;
}

// 运营数据统计相关类型
export interface TrendData {
  date: string;
  count: number;
}

export interface DistributionData {
  [key: string]: any;
  count: number;
}

export interface UserStats {
  total_users: number;
  new_users_today: number;
  new_users_this_week: number;
  new_users_this_month: number;
  active_users_today: number;
  active_users_this_week: number;
  active_users_this_month: number;
  admin_users_count: number;
  system_admin_users_count: number;
  user_registration_trend: TrendData[];
  user_activity_trend: TrendData[];
}

export interface TaskStats {
  total_tasks: number;
  pending_tasks: number;
  processing_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  tasks_today: number;
  tasks_this_week: number;
  tasks_this_month: number;
  avg_processing_time?: number;
  success_rate: number;
  task_creation_trend: TrendData[];
  task_completion_trend: TrendData[];
  task_status_distribution: DistributionData[];
}

export interface SystemStats {
  total_files: number;
  total_file_size: number;
  files_today: number;
  files_this_week: number;
  files_this_month: number;
  total_ai_calls: number;
  ai_calls_today: number;
  ai_calls_this_week: number;
  ai_calls_this_month: number;
  avg_ai_processing_time?: number;
  file_type_distribution: DistributionData[];
  ai_model_usage: DistributionData[];
}

export interface IssueStats {
  total_issues: number;
  issues_by_severity: DistributionData[];
  issues_by_type: DistributionData[];
  feedback_stats: { [key: string]: number };
  recent_issues: any[];
  issue_trend: TrendData[];
  satisfaction_stats: {
    average_rating: number;
    rating_distribution: { rating: number; count: number }[];
    total_ratings: number;
    high_satisfaction_rate: number;
    low_satisfaction_rate: number;
  };
}

export interface ErrorStats {
  total_errors: number;
  errors_today: number;
  errors_this_week: number;
  error_types: DistributionData[];
  recent_errors: any[];
}

export interface AnalyticsData {
  user_stats: UserStats;
  task_stats: TaskStats;
  system_stats: SystemStats;
  issue_stats: IssueStats;
  error_stats: ErrorStats;
  last_updated: string;
}