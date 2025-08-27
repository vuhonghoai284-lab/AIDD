import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Card, Button, Tag, Progress, Space, message, Spin, Empty, 
  Input, Radio, Tabs, Typography, Pagination, Collapse, Badge,
  Divider, Row, Col, Tooltip, Alert, Dropdown, Rate
} from 'antd';
import { 
  ArrowLeftOutlined, DownloadOutlined, CheckOutlined, CloseOutlined, 
  FileTextOutlined, ExclamationCircleOutlined, BulbOutlined,
  ThunderboltOutlined, UserOutlined, QuestionCircleOutlined,
  HistoryOutlined, RobotOutlined, InfoCircleOutlined, SwapOutlined,
  EnvironmentOutlined, EditOutlined, DownOutlined, StarOutlined,
  WarningOutlined, FireOutlined, InfoOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { taskAPI } from '../api';
import { TaskDetail as TaskDetailType, Issue, AIOutput } from '../types';
import TaskLogs from '../components/TaskLogs';
import { formatInputText, formatJSON, decodeUnicode, isLikelyJSON } from '../utils/textFormatter';
import './TaskDetailEnhanced.css';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;
const { TextArea } = Input;

// 扩展Issue类型以包含新字段
interface EnhancedIssue extends Issue {
  original_text?: string;
  user_impact?: string;
  reasoning?: string;
  context?: string;
  satisfaction_rating?: number;  // 满意度评分 1-5星
}

interface EnhancedTaskDetail extends TaskDetailType {
  issues: EnhancedIssue[];
}

const TaskDetailEnhanced: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [taskDetail, setTaskDetail] = useState<EnhancedTaskDetail | null>(null);
  const [issues, setIssues] = useState<EnhancedIssue[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [issuesTotal, setIssuesTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [feedbackLoading, setFeedbackLoading] = useState<{ [key: number]: boolean }>({});
  const [aiOutputs, setAiOutputs] = useState<AIOutput[]>([]);
  const [aiOutputsLoading, setAiOutputsLoading] = useState(false);
  
  // 报告下载相关状态
  const [downloadPermission, setDownloadPermission] = useState<any>(null);
  const [downloadLoading, setDownloadLoading] = useState(false);
  
  // 使用 useRef 来存储定时器和状态，避免依赖问题
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const taskStatusRef = useRef<string | undefined>(undefined);
  
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [expandedIssues, setExpandedIssues] = useState<Set<number>>(new Set());
  const [expandedSections, setExpandedSections] = useState<{ [key: number]: Set<string> }>({});
  const [expandedComments, setExpandedComments] = useState<Set<number>>(new Set());
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [aiOutputFilter, setAiOutputFilter] = useState<string>('all');
  const [aiStatusFilter, setAiStatusFilter] = useState<string>('all');
  const [aiOutputsLoaded, setAiOutputsLoaded] = useState(false); // 跟踪是否已加载AI输出
  const [aiCurrentPage, setAiCurrentPage] = useState(1);
  const [aiPageSize] = useState(5); // AI输出每页较少，减少加载时间
  const [aiOutputsTotal, setAiOutputsTotal] = useState(0); // AI输出总数

  const loadTaskDetail = useCallback(async () => {
    if (!id) return;
    
    try {
      const data = await taskAPI.getTaskDetail(parseInt(id));
      setTaskDetail(data as EnhancedTaskDetail);
      
      // 更新状态引用
      taskStatusRef.current = data.task.status;
      
      // 如果任务完成，检查下载权限
      if (data.task.status === 'completed') {
        await checkDownloadPermission(parseInt(id));
      }
    } catch (error) {
      message.error('加载任务详情失败');
      console.error(error);
    }
    setLoading(false);
  }, [id]);

  const loadIssues = useCallback(async (page: number = 1, pageSize: number = 10) => {
    if (!id) return;
    
    setIssuesLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        search: undefined,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        issue_type: undefined,
        feedback_status: statusFilter !== 'all' ? statusFilter : undefined,
        sort_by: 'id',
        sort_order: 'desc' as const
      };
      
      const response = await taskAPI.getTaskIssues(parseInt(id), params);
      setIssues(response.items as EnhancedIssue[]);
      setIssuesTotal(response.total);
    } catch (error) {
      message.error('加载问题列表失败');
      console.error(error);
    }
    setIssuesLoading(false);
  }, [id, severityFilter, statusFilter]);

  const loadAIOutputs = useCallback(async (page: number = 1, pageSize: number = aiPageSize, forceReload = false) => {
    if (!id) return;
    
    // 如果已加载且不是强制重载，跳过
    if (aiOutputsLoaded && !forceReload && page === 1) {
      return;
    }
    
    setAiOutputsLoading(true);
    try {
      // 使用分页API加载AI输出
      const params = {
        page,
        page_size: pageSize,
        operation_type: aiOutputFilter !== 'all' ? aiOutputFilter : undefined,
        sort_by: 'id',
        sort_order: 'desc' as const
      };
      
      // 添加超时处理，防止请求挂起
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('AI输出加载超时')), 10000)
      );
      
      const outputsPromise = taskAPI.getTaskAIOutputsPaginated(parseInt(id), params);
      const response = await Promise.race([outputsPromise, timeoutPromise]) as any;
      
      if (page === 1) {
        // 第一页，替换数据
        setAiOutputs(response.items || []);
        setAiOutputsLoaded(true); // 标记已加载
      } else {
        // 后续页，追加数据（用于无限滚动）
        setAiOutputs(prev => [...prev, ...(response.items || [])]);
      }
      
      // 存储总数信息
      if (response.total !== undefined) {
        setAiOutputsTotal(response.total);
        setAiOutputs(prev => Object.assign(prev, { _total: response.total }));
      }
    } catch (error: any) {
      // AI输出加载失败不影响主页面显示
      if (process.env.NODE_ENV === 'development') {
        console.warn('AI输出加载失败:', error);
      }
      // 只在非超时情况下显示错误信息
      if (!error.message?.includes('超时')) {
        message.warning('AI输出加载失败，但不影响任务详情查看');
      }
    } finally {
      setAiOutputsLoading(false);
    }
  }, [id, aiOutputFilter, aiPageSize, aiOutputsLoaded]);

  useEffect(() => {
    // 先加载任务详情，成功后再加载问题
    loadTaskDetail().then(() => {
      // 加载问题列表
      loadIssues(currentPage, pageSize);
      // AI输出改为懒加载，只有用户点击标签页时才加载
    });
  }, [loadTaskDetail]); // 移除loadAIOutputs依赖，改为按需加载

  // 分页、过滤条件变化时重新加载问题
  useEffect(() => {
    if (taskDetail) {
      loadIssues(currentPage, pageSize);
    }
  }, [currentPage, pageSize, severityFilter, statusFilter, taskDetail]);

  // 清理定时器 useEffect - 仅在组件卸载时清理
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []); // 空依赖数组，仅在组件卸载时执行

  const handleFeedback = useCallback(async (issueId: number, feedbackType: 'accept' | 'reject', comment?: string) => {
    setFeedbackLoading(prev => ({ ...prev, [issueId]: true }));
    try {
      await taskAPI.submitFeedback(issueId, feedbackType, comment);
      message.success('反馈已提交');
      await loadTaskDetail();
      await loadIssues(currentPage, pageSize); // 重新加载当前页问题
      
      // 提交反馈后重新检查下载权限（可能影响下载权限）
      if (id && taskDetail?.task.status === 'completed') {
        await checkDownloadPermission(parseInt(id));
      }
    } catch (error) {
      message.error('提交反馈失败');
    }
    setFeedbackLoading(prev => ({ ...prev, [issueId]: false }));
  }, [id, taskDetail?.task.status, loadTaskDetail, loadIssues, currentPage, pageSize]);

  const handleQuickFeedback = useCallback(async (issueId: number, feedbackType: 'accept' | 'reject' | null, comment?: string) => {
    setFeedbackLoading(prev => ({ ...prev, [issueId]: true }));
    
    try {
      if (feedbackType === null) {
        // 重新处理：清除之前的反馈，通过提交空的反馈类型来实现
        await taskAPI.submitFeedback(issueId, '', comment);
        message.success('已重置，可重新处理');
      } else {
        await taskAPI.submitFeedback(issueId, feedbackType, comment);
        message.success(
          feedbackType === 'accept' ? '已接受此问题' : '已拒绝此问题',
          1.5
        );
      }
      await loadTaskDetail();
      await loadIssues(currentPage, pageSize); // 重新加载当前页问题
    } catch (error) {
      message.error('操作失败');
    }
    
    setFeedbackLoading(prev => ({ ...prev, [issueId]: false }));
  }, [loadTaskDetail, loadIssues, currentPage, pageSize]);

  // 检查下载权限 - 内联函数避免依赖问题
  const checkDownloadPermission = async (taskId: number) => {
    try {
      const permission = await taskAPI.checkReportPermission(taskId);
      setDownloadPermission(permission);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('检查下载权限失败:', error);
      }
      setDownloadPermission({ 
        can_download: false, 
        reason: '检查权限失败' 
      });
    }
  };

  const handleDownloadReport = useCallback(async () => {
    if (!taskDetail) return;
    
    // 如果没有权限，显示详细提示
    if (downloadPermission && !downloadPermission.can_download) {
      if (downloadPermission.total_issues && downloadPermission.unprocessed_count) {
        message.warning({
          content: `请先处理完所有问题才能下载报告！还有 ${downloadPermission.unprocessed_count} 个问题需要处理（共 ${downloadPermission.total_issues} 个问题）`,
          duration: 5,
        });
      } else {
        message.warning({
          content: downloadPermission.reason || '暂无下载权限',
          duration: 4,
        });
      }
      return;
    }
    
    setDownloadLoading(true);
    try {
      const result = await taskAPI.downloadReport(taskDetail.task.id);
      message.success(`报告下载成功: ${result.filename}`);
      
      // 下载成功后重新检查权限状态
      await checkDownloadPermission(taskDetail.task.id);
    } catch (error: any) {
      if (process.env.NODE_ENV === 'development') {
        console.error('下载报告失败:', error);
      }
      
      // 处理权限错误
      if (error.response?.status === 403) {
        const errorData = error.response.data;
        if (errorData.total_issues && errorData.unprocessed_count) {
          message.error({
            content: `下载失败：还有 ${errorData.unprocessed_count} 个问题需要处理（共 ${errorData.total_issues} 个问题）`,
            duration: 5,
          });
        } else {
          message.error(errorData.detail || '下载权限不足');
        }
      } else {
        message.error('下载报告失败，请稍后重试');
      }
    } finally {
      setDownloadLoading(false);
    }
  }, [taskDetail, downloadPermission]);

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string } } = {
      pending: { color: 'default', text: '等待中' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const config = statusMap[status] || statusMap.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getSeverityBadge = (severity: string, prominent: boolean = false) => {
    const severityMap: { [key: string]: { 
      color: string; 
      icon: React.ReactNode; 
      tagColor: string;
      bgColor: string;
      textColor: string;
    } } = {
      '致命': { 
        color: 'red', 
        icon: <FireOutlined />, 
        tagColor: 'error',
        bgColor: '#ffebee',
        textColor: '#c62828'
      },
      '严重': { 
        color: 'orange', 
        icon: <WarningOutlined />, 
        tagColor: 'warning',
        bgColor: '#fff8e1',
        textColor: '#e65100'
      },
      '一般': { 
        color: 'blue', 
        icon: <InfoOutlined />, 
        tagColor: 'processing',
        bgColor: '#e3f2fd',
        textColor: '#1565c0'
      },
      '提示': { 
        color: 'green', 
        icon: <BulbOutlined />, 
        tagColor: 'success',
        bgColor: '#e8f5e8',
        textColor: '#2e7d32'
      }
    };
    const config = severityMap[severity] || severityMap['一般'];
    
    if (prominent) {
      return (
        <div className={`severity-badge severity-${severity.toLowerCase()}`} style={{
          background: config.bgColor,
          color: config.textColor,
          padding: '6px 12px',
          borderRadius: '6px',
          fontWeight: '600',
          fontSize: '14px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          border: `1px solid ${config.color}20`
        }}>
          {config.icon}
          <span>{severity}级别</span>
        </div>
      );
    }
    
    return (
      <Tag color={config.tagColor} icon={config.icon}>
        {severity}
      </Tag>
    );
  };

  const toggleIssueExpanded = useCallback((issueId: number) => {
    setExpandedIssues(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(issueId)) {
        newExpanded.delete(issueId);
      } else {
        newExpanded.add(issueId);
      }
      return newExpanded;
    });
  }, []);

  const toggleSection = useCallback((issueId: number, section: string) => {
    setExpandedSections(prev => {
      const current = prev[issueId] || new Set();
      const newSet = new Set(current);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return { ...prev, [issueId]: newSet };
    });
  }, []);

  const toggleComment = useCallback((issueId: number) => {
    setExpandedComments(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(issueId)) {
        newExpanded.delete(issueId);
      } else {
        newExpanded.add(issueId);
      }
      return newExpanded;
    });
  }, []);

  const handleTabChange = useCallback((activeKey: string) => {
    // 当切换到AI输出标签页时，懒加载AI输出数据
    if (activeKey === 'ai-outputs' && !aiOutputsLoaded) {
      loadAIOutputs(1, aiPageSize);
    }
  }, [aiOutputsLoaded, loadAIOutputs, aiPageSize]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!taskDetail) {
    return <Empty description="任务不存在" />;
  }

  const { task } = taskDetail;
  
  // 使用新的issues状态
  const totalIssues = issuesTotal;
  const displayIssues = issues; // 当前页面显示的问题

  // 统计信息 - 使用从API获取的统计数据或计算当前页面数据
  const processedCount = issues.filter(i => i.feedback_type).length;
  const acceptedCount = issues.filter(i => i.feedback_type === 'accept').length;
  const severityCounts = {
    '致命': issues.filter(i => i.severity === '致命').length,
    '严重': issues.filter(i => i.severity === '严重').length,
    '一般': issues.filter(i => i.severity === '一般').length,
    '提示': issues.filter(i => i.severity === '提示').length
  };

  return (
    <div className="task-detail-enhanced" style={{ maxWidth: '100%', padding: '0 24px' }}>
      {/* Enhanced Task Detail Page v3 - Compact Layout */}
      <Card
        className="main-card"
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
              返回列表
            </Button>
            <span className="task-title">{task.title}</span>
          </Space>
        }
        extra={
          task.status === 'completed' && (
            <Space>
              {/* 权限提示信息 */}
              {downloadPermission && !downloadPermission.can_download && downloadPermission.total_issues && (
                <Tooltip title={`还有 ${downloadPermission.unprocessed_count} 个问题需要处理`}>
                  <Badge count={downloadPermission.unprocessed_count} offset={[10, 0]}>
                    <InfoCircleOutlined style={{ color: '#faad14', fontSize: '16px' }} />
                  </Badge>
                </Tooltip>
              )}
              
              {/* 下载按钮 */}
              <Tooltip 
                title={
                  downloadPermission?.can_download 
                    ? '点击下载Excel格式的质量检测报告' 
                    : downloadPermission?.reason || '检查权限中...'
                }
              >
                <Button 
                  type={downloadPermission?.can_download ? "primary" : "default"}
                  icon={<DownloadOutlined />} 
                  onClick={handleDownloadReport}
                  loading={downloadLoading}
                  disabled={downloadPermission && !downloadPermission.can_download}
                >
                  {downloadLoading ? '生成中...' : 
                   downloadPermission?.can_download ? '下载报告' : 
                   downloadPermission ? '需处理问题' : '检查中...'}
                </Button>
              </Tooltip>
            </Space>
          )
        }
      >
        {/* 任务基本信息 */}
        <Card className="info-card" size="small" title="任务信息">
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Text type="secondary">文件名</Text>
              <div>{task.file_name}</div>
            </Col>
            <Col span={5}>
              <Text type="secondary">状态</Text>
              <div>{getStatusTag(task.status)}</div>
            </Col>
            <Col span={7}>
              <Text type="secondary">进度</Text>
              <Progress percent={Math.round(task.progress)} size="small" />
            </Col>
            <Col span={4}>
              <Text type="secondary">文件类型</Text>
              <div><Tag>{task.file_type?.toUpperCase() || 'UNKNOWN'}</Tag></div>
            </Col>
          </Row>
        </Card>

        {/* 标签页 */}
        <Tabs 
          defaultActiveKey={task.status === 'processing' ? 'logs' : 'issues'}
          onChange={handleTabChange}
        >
          {/* 问题列表标签页 */}
          <Tabs.TabPane 
            tab={
              <Space>
                <FileTextOutlined />
                <span>检测问题 ({totalIssues})</span>
              </Space>
            } 
            key="issues"
          >
            {task.status === 'completed' && (
              <>
                {totalIssues === 0 ? (
                  <Empty description="未发现任何问题" />
                ) : (
                  <>
                    {/* 筛选器 */}
                    <Card className="filter-card" size="small" style={{ marginBottom: 16 }}>
                      <Space size={16} wrap>
                        <Space size={8}>
                          <Text strong>问题级别:</Text>
                          <Radio.Group 
                            value={severityFilter} 
                            onChange={(e) => {
                              setSeverityFilter(e.target.value);
                              setCurrentPage(1);
                            }}
                            size="small"
                          >
                            <Radio.Button value="all">全部</Radio.Button>
                            <Radio.Button value="致命">
                              <Tag color="error">致命</Tag>
                            </Radio.Button>
                            <Radio.Button value="严重">
                              <Tag color="warning">严重</Tag>
                            </Radio.Button>
                            <Radio.Button value="一般">
                              <Tag color="processing">一般</Tag>
                            </Radio.Button>
                            <Radio.Button value="提示">
                              <Tag color="success">提示</Tag>
                            </Radio.Button>
                          </Radio.Group>
                        </Space>
                        <Divider type="vertical" />
                        <Space size={8}>
                          <Text strong>处理状态:</Text>
                          <Radio.Group 
                            value={statusFilter} 
                            onChange={(e) => {
                              setStatusFilter(e.target.value);
                              setCurrentPage(1);
                            }}
                            size="small"
                          >
                            <Radio.Button value="all">全部</Radio.Button>
                            <Radio.Button value="accepted">
                              <CheckOutlined style={{ color: '#52c41a' }} /> 已接受
                            </Radio.Button>
                            <Radio.Button value="rejected">
                              <CloseOutlined style={{ color: '#ff4d4f' }} /> 已拒绝
                            </Radio.Button>
                            <Radio.Button value="pending">
                              <QuestionCircleOutlined /> 未处理
                            </Radio.Button>
                          </Radio.Group>
                        </Space>
                        <Tag color="blue">显示 {displayIssues.length} 个问题</Tag>
                      </Space>
                    </Card>

                    {/* 问题统计 - 改进版 */}
                    <Card className="statistics-card" size="small" style={{ marginBottom: 16 }}>
                      <Row gutter={24}>
                        <Col span={8}>
                          <div className="stat-section">
                            <Text type="secondary">处理进度</Text>
                            <Progress 
                              percent={Math.round((processedCount / totalIssues) * 100)} 
                              status="active"
                              strokeColor="#1890ff"
                            />
                            <div className="stat-detail">
                              <Text>已处理: {processedCount}/{totalIssues}</Text>
                              <Text type="success"> | 已接受: {acceptedCount}</Text>
                            </div>
                          </div>
                        </Col>
                        <Col span={8}>
                          <div className="stat-section">
                            <Text type="secondary">问题级别分布</Text>
                            <div className="severity-bars">
                              <div className="bar-item">
                                <Text>致命</Text>
                                <Progress 
                                  percent={totalIssues ? Math.round((severityCounts['致命'] / totalIssues) * 100) : 0} 
                                  size="small"
                                  strokeColor="#ff4d4f"
                                  format={() => severityCounts['致命']}
                                />
                              </div>
                              <div className="bar-item">
                                <Text>严重</Text>
                                <Progress 
                                  percent={totalIssues ? Math.round((severityCounts['严重'] / totalIssues) * 100) : 0}
                                  size="small"
                                  strokeColor="#faad14"
                                  format={() => severityCounts['严重']}
                                />
                              </div>
                              <div className="bar-item">
                                <Text>一般</Text>
                                <Progress 
                                  percent={totalIssues ? Math.round((severityCounts['一般'] / totalIssues) * 100) : 0}
                                  size="small"
                                  strokeColor="#1890ff"
                                  format={() => severityCounts['一般']}
                                />
                              </div>
                              <div className="bar-item">
                                <Text>提示</Text>
                                <Progress 
                                  percent={totalIssues ? Math.round((severityCounts['提示'] / totalIssues) * 100) : 0}
                                  size="small"
                                  strokeColor="#52c41a"
                                  format={() => severityCounts['提示']}
                                />
                              </div>
                            </div>
                          </div>
                        </Col>
                        <Col span={8}>
                          <div className="stat-section">
                            <Text type="secondary">接受率</Text>
                            <div className="acceptance-rate">
                              <Progress 
                                type="circle" 
                                percent={processedCount ? Math.round((acceptedCount / processedCount) * 100) : 0}
                                width={80}
                                strokeColor={{
                                  '0%': '#52c41a',
                                  '100%': '#87d068',
                                }}
                              />
                              <div className="rate-detail">
                                <Text>接受: {acceptedCount}</Text>
                                <br />
                                <Text>拒绝: {processedCount - acceptedCount}</Text>
                              </div>
                            </div>
                          </div>
                        </Col>
                      </Row>
                    </Card>

                    {/* 问题列表 - 优化设计 */}
                    <div className="issues-list">
                      {issuesLoading ? (
                        <div style={{ textAlign: 'center', padding: 50 }}>
                          <Spin size="large" tip="加载问题中..." />
                        </div>
                      ) : displayIssues.length > 0 ? (
                        displayIssues.map((issue, index) => (
                        <Card 
                          key={issue.id} 
                          className={`issue-card-enhanced issue-severity-${issue.severity.toLowerCase()} ${issue.feedback_type ? 'processed' : 'pending'}`}
                          size="small"
                        >
                          {/* 第一行：问题编号 + 级别 + 错误类型 + 状态 */}
                          <div className="issue-header-compact">
                            <div className="issue-header-top">
                              <div className="issue-meta-info">
                                <Space size={12} align="center">
                                  <span className="issue-number">#{(currentPage - 1) * pageSize + index + 1}</span>
                                  {getSeverityBadge(issue.severity, false)}
                                  <Tag color="blue" className="issue-type-tag">[{issue.issue_type}]</Tag>
                                </Space>
                              </div>
                              <div className="issue-status-section">
                                {issue.feedback_type ? (
                                  <Tag 
                                    icon={issue.feedback_type === 'accept' ? <CheckOutlined /> : <CloseOutlined />} 
                                    color={issue.feedback_type === 'accept' ? 'success' : 'error'}
                                    style={{ fontSize: '12px' }}
                                  >
                                    {issue.feedback_type === 'accept' ? '已接受' : '已拒绝'}
                                  </Tag>
                                ) : (
                                  <Tag color="default" style={{ fontSize: '12px' }}>
                                    待处理
                                  </Tag>
                                )}
                              </div>
                            </div>
                            {/* 第二行：问题描述（独立显示，可以换行） */}
                            <div className="issue-description-full">
                              <Text 
                                className="issue-description-text" 
                                style={{ 
                                  fontWeight: '500', 
                                  color: '#262626',
                                  display: 'block',
                                  lineHeight: '1.4',
                                  marginTop: '8px',
                                  wordBreak: 'break-word'
                                }}
                              >
                                {decodeUnicode(issue.description)}
                              </Text>
                            </div>
                          </div>

                          {/* 第二行：原文内容（单行显示） */}
                          {issue.original_text && (
                            <div className="issue-content-row">
                              <div className="content-section original">
                                <Text style={{ fontSize: 13, lineHeight: 1.5, color: '#595959' }}>
                                  <FileTextOutlined style={{ color: '#ff7875', marginRight: 6 }} />
                                  <Text strong style={{ color: '#ff7875', marginRight: 8 }}>原文内容：</Text>
                                  {decodeUnicode(issue.original_text)}
                                </Text>
                              </div>
                            </div>
                          )}

                          {/* 第三行：改进建议（单行显示） */}
                          {issue.suggestion && (
                            <div className="issue-content-row">
                              <div className="content-section suggestion">
                                <Text style={{ fontSize: 13, lineHeight: 1.5, color: '#595959' }}>
                                  <EditOutlined style={{ color: '#73d13d', marginRight: 6 }} />
                                  <Text strong style={{ color: '#73d13d', marginRight: 8 }}>改进建议：</Text>
                                  {decodeUnicode(issue.suggestion)}
                                </Text>
                              </div>
                            </div>
                          )}

                          {/* 操作行：快速操作 + 满意度评分（右侧） */}
                          <div className="issue-actions-row">
                            <div className="actions-left">
                              {!issue.feedback_type ? (
                                <Space size={8}>
                                  <Button
                                    type="primary"
                                    size="small"
                                    icon={<CheckOutlined />}
                                    loading={feedbackLoading[issue.id]}
                                    onClick={() => handleQuickFeedback(issue.id, 'accept')}
                                  >
                                    接受
                                  </Button>
                                  <Button
                                    danger
                                    size="small"
                                    icon={<CloseOutlined />}
                                    loading={feedbackLoading[issue.id]}
                                    onClick={() => handleQuickFeedback(issue.id, 'reject')}
                                  >
                                    拒绝
                                  </Button>
                                  <Button
                                    type="text"
                                    size="small"
                                    icon={<FileTextOutlined />}
                                    onClick={() => toggleComment(issue.id)}
                                  >
                                    {issue.feedback_comment ? '编辑评论' : '添加评论'}
                                  </Button>
                                </Space>
                              ) : (
                                <Space size={8}>
                                  <Text type="secondary" style={{ fontSize: 13 }}>
                                    已{issue.feedback_type === 'accept' ? '接受' : '拒绝'}
                                  </Text>
                                  <Button
                                    type="link"
                                    size="small"
                                    onClick={() => handleQuickFeedback(issue.id, null)}
                                  >
                                    重新处理
                                  </Button>
                                  {issue.feedback_comment && (
                                    <Tooltip title={issue.feedback_comment}>
                                      <Tag icon={<FileTextOutlined />} color="blue" style={{ fontSize: 11 }}>有评论</Tag>
                                    </Tooltip>
                                  )}
                                </Space>
                              )}
                            </div>
                            <div className="actions-right">
                              <div className="satisfaction-rating-compact">
                                <Space size={8} align="center">
                                  <Text style={{ fontSize: 12, color: '#8c8c8c' }}>满意度：</Text>
                                  <Rate
                                    allowHalf
                                    value={issue.satisfaction_rating || 0}
                                    onChange={async (value) => {
                                      try {
                                        // 更新当前显示的问题列表
                                        const newIssues = [...issues];
                                        const idx = newIssues.findIndex(i => i.id === issue.id);
                                        if (idx >= 0) {
                                          newIssues[idx].satisfaction_rating = value;
                                          setIssues(newIssues);
                                        }
                                        await taskAPI.submitSatisfactionRating(issue.id, value);
                                        message.success('评分已保存');
                                      } catch (error) {
                                        message.error('评分保存失败');
                                      }
                                    }}
                                    style={{ fontSize: 14 }}
                                  />
                                  {issue.satisfaction_rating && (
                                    <Text style={{ fontSize: 11, color: '#8c8c8c' }}>
                                      {issue.satisfaction_rating}星
                                    </Text>
                                  )}
                                </Space>
                              </div>
                            </div>
                          </div>

                          {/* 详情信息 - 默认折叠 */}
                          <div className="details-section">
                            <Collapse 
                              ghost 
                              className="details-collapse"
                              activeKey={expandedSections[issue.id]?.has('details') ? ['details'] : []}
                              onChange={() => toggleSection(issue.id, 'details')}
                            >
                              <Panel
                                header={
                                  <Space size={4}>
                                    <InfoCircleOutlined style={{ color: '#1890ff' }} />
                                    <Text>详细信息</Text>
                                  </Space>
                                }
                                key="details"
                              >
                                {/* 原文对比展示 */}
                                {(issue.original_text || issue.suggestion) && (
                                  <div className="comparison-section">
                                    <Row gutter={16}>
                                      <Col span={12}>
                                        <div className="comparison-box">
                                          <div className="comparison-header">
                                            <FileTextOutlined style={{ color: '#ff4d4f' }} />
                                            <Text strong> 原文内容</Text>
                                          </div>
                                          <div className="comparison-content">
                                            {issue.original_text ? decodeUnicode(issue.original_text) : '未提供原文'}
                                          </div>
                                        </div>
                                      </Col>
                                      <Col span={12}>
                                        <div className="comparison-box">
                                          <div className="comparison-header">
                                            <EditOutlined style={{ color: '#52c41a' }} />
                                            <Text strong> 改进建议</Text>
                                          </div>
                                          <div className="comparison-content">
                                            {issue.suggestion ? decodeUnicode(issue.suggestion) : '未提供建议'}
                                          </div>
                                        </div>
                                      </Col>
                                    </Row>
                                  </div>
                                )}

                                {/* 详细分析 */}
                                <div className="more-info-content">
                                  {issue.location && (
                                    <div className="info-item">
                                      <EnvironmentOutlined style={{ color: '#8c8c8c' }} />
                                      <Text strong> 章节位置：</Text>
                                      <Text>{issue.location}</Text>
                                    </div>
                                  )}
                                  {issue.reasoning && (
                                    <div className="info-item">
                                      <ThunderboltOutlined style={{ color: '#1890ff' }} />
                                      <Text strong> 判定原因：</Text>
                                      <Text>{decodeUnicode(issue.reasoning)}</Text>
                                    </div>
                                  )}
                                  {issue.user_impact && (
                                    <div className="info-item">
                                      <UserOutlined style={{ color: '#faad14' }} />
                                      <Text strong> 用户影响：</Text>
                                      <Text>{decodeUnicode(issue.user_impact)}</Text>
                                    </div>
                                  )}
                                  {issue.context && (
                                    <div className="info-item">
                                      <FileTextOutlined style={{ color: '#722ed1' }} />
                                      <Text strong> 上下文环境：</Text>
                                      <Text>{decodeUnicode(issue.context)}</Text>
                                    </div>
                                  )}
                                </div>
                              </Panel>
                            </Collapse>
                          </div>

                          {/* 评论输入区（可展开） */}
                          {expandedComments.has(issue.id) && (
                            <div className="comment-section">
                              <div className="comment-input-area">
                                <div className="comment-header">
                                  <UserOutlined style={{ color: '#1890ff' }} />
                                  <Text strong> 添加评论</Text>
                                </div>
                                <TextArea
                                  placeholder="请输入反馈意见..."
                                  rows={3}
                                  value={issue.feedback_comment || ''}
                                  onChange={(e) => {
                                    const newIssues = [...issues];
                                    const idx = newIssues.findIndex(i => i.id === issue.id);
                                    if (idx >= 0) {
                                      newIssues[idx].feedback_comment = e.target.value;
                                      setIssues(newIssues);
                                    }
                                  }}
                                  className="comment-textarea"
                                />
                                <div className="comment-actions">
                                  <Space size={8}>
                                    <Dropdown
                                      trigger={['click']}
                                      menu={{
                                        items: [
                                          { key: '1', label: '同意此建议' },
                                          { key: '2', label: '不适用于当前文档' },
                                          { key: '3', label: '需要进一步确认' },
                                          { key: '4', label: '误报' },
                                          { key: '5', label: '自定义输入...' },
                                        ],
                                        onClick: ({ key }) => {
                                          const templates = [
                                            '同意此建议',
                                            '不适用于当前文档',
                                            '需要进一步确认',
                                            '误报',
                                            ''
                                          ];
                                          const template = templates[parseInt(key) - 1] || '';
                                          
                                          if (template) {
                                            const newIssues = [...issues];
                                            const idx = newIssues.findIndex(i => i.id === issue.id);
                                            if (idx >= 0) {
                                              newIssues[idx].feedback_comment = template;
                                              setIssues(newIssues);
                                            }
                                          }
                                        }
                                      }}
                                    >
                                      <Button size="small" type="dashed">
                                        快速模板 <DownOutlined />
                                      </Button>
                                    </Dropdown>
                                    <Button 
                                      size="small" 
                                      type="primary"
                                      onClick={async () => {
                                        try {
                                          // 如果已有反馈类型，更新整个反馈；否则只保存评论
                                          if (issue.feedback_type) {
                                            await handleFeedback(issue.id, issue.feedback_type, issue.feedback_comment);
                                          } else {
                                            // 使用新的API只更新评论，不改变反馈状态
                                            await taskAPI.updateCommentOnly(issue.id, issue.feedback_comment);
                                            // 重新加载任务详情和问题列表以获取最新的评论
                                            await loadTaskDetail();
                                            await loadIssues(currentPage, pageSize);
                                          }
                                          message.success('评论已保存');
                                          toggleComment(issue.id);
                                        } catch (error) {
                                          message.error('评论保存失败');
                                        }
                                      }}
                                    >
                                      保存评论
                                    </Button>
                                    <Button 
                                      size="small"
                                      onClick={() => toggleComment(issue.id)}
                                    >
                                      取消
                                    </Button>
                                  </Space>
                                </div>
                              </div>
                            </div>
                          )}
                        </Card>
                        ))
                      ) : (
                        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                          <Empty 
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={
                              <div>
                                <Text type="secondary" style={{ fontSize: '16px' }}>
                                  {totalIssues === 0 ? '暂无问题记录' : '当前筛选条件下无问题'}
                                </Text>
                                {totalIssues === 0 && task.status === 'completed' && (
                                  <div style={{ marginTop: '8px' }}>
                                    <Text type="secondary" style={{ fontSize: '14px' }}>
                                      🎉 恭喜！此文档没有发现问题
                                    </Text>
                                  </div>
                                )}
                                {totalIssues > 0 && (
                                  <div style={{ marginTop: '8px' }}>
                                    <Button 
                                      type="link" 
                                      onClick={() => {
                                        setSeverityFilter('all');
                                        setStatusFilter('all');
                                      }}
                                    >
                                      清除筛选条件
                                    </Button>
                                  </div>
                                )}
                              </div>
                            }
                          />
                        </div>
                      )}
                    </div>

                    {/* 分页器 */}
                    {totalIssues > 0 && (
                      <div className="pagination-container">
                        <Pagination
                          current={currentPage}
                          pageSize={pageSize}
                          total={totalIssues}
                          onChange={(page) => {
                            setCurrentPage(page);
                            loadIssues(page, pageSize);
                          }}
                          onShowSizeChange={(_, size) => {
                            setPageSize(size);
                            setCurrentPage(1);
                            loadIssues(1, size);
                          }}
                          showSizeChanger
                          showQuickJumper
                          showTotal={(total) => `共 ${total} 个问题`}
                          pageSizeOptions={['5', '10', '20', '50']}
                        />
                      </div>
                    )}
                  </>
                )}
              </>
            )}

            {/* 处理中状态 */}
            {(task.status === 'pending' || task.status === 'processing') && (
              <Card>
                <div style={{ textAlign: 'center', padding: 50 }}>
                  <Spin size="large" />
                  <p style={{ marginTop: 16 }}>任务正在处理中，请稍候...</p>
                  <Progress percent={Math.round(task.progress)} />
                </div>
              </Card>
            )}
          </Tabs.TabPane>

          {/* 实时日志标签页 */}
          <Tabs.TabPane 
            tab={
              <Space>
                <HistoryOutlined />
                <span>实时日志</span>
              </Space>
            } 
            key="logs"
          >
            <TaskLogs taskId={id} taskStatus={task.status} />
          </Tabs.TabPane>

          {/* AI输出标签页 */}
          <Tabs.TabPane 
            tab={
              <Space>
                <RobotOutlined />
                <span>AI输出 ({aiOutputsLoaded ? aiOutputsTotal : '..'})</span>
              </Space>
            } 
            key="ai-outputs"
          >
            {aiOutputsLoading ? (
              <div style={{ textAlign: 'center', padding: 50 }}>
                <Spin size="large" tip="加载AI输出中..." />
              </div>
            ) : aiOutputs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <Empty 
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: '16px' }}>
                        暂无AI输出记录
                      </Text>
                      <div style={{ marginTop: '8px' }}>
                        <Text type="secondary" style={{ fontSize: '14px' }}>
                          {task.status === 'pending' && '任务尚未开始处理'}
                          {task.status === 'processing' && '任务正在处理中，输出记录将陆续生成'}
                          {task.status === 'failed' && '任务处理失败，无输出记录'}
                          {task.status === 'completed' && '此任务没有生成AI输出记录'}
                        </Text>
                      </div>
                      {task.status === 'failed' && (
                        <div style={{ marginTop: '12px' }}>
                          <Button 
                            type="primary" 
                            size="small"
                            onClick={() => {
                              // 这里可以添加重试逻辑
                              navigate(`/task/${task.id}`);
                            }}
                          >
                            查看错误详情
                          </Button>
                        </div>
                      )}
                    </div>
                  }
                />
              </div>
            ) : (
              <>
                {/* AI输出筛选器 */}
                <Card className="filter-card" size="small" style={{ marginBottom: 16 }}>
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Space size={16} wrap>
                        <Space size={8}>
                          <Text strong>操作类型:</Text>
                          <Radio.Group 
                            value={aiOutputFilter} 
                            onChange={(e) => {
                              setAiOutputFilter(e.target.value);
                              // 过滤条件变化时重新加载第一页
                              if (aiOutputsLoaded) {
                                setAiCurrentPage(1);
                                loadAIOutputs(1, aiPageSize, true);
                              }
                            }}
                            size="small"
                          >
                            <Radio.Button value="all">
                              全部 ({aiOutputs.length})
                            </Radio.Button>
                            <Radio.Button value="preprocess">
                              <Tag color="blue">预处理 ({aiOutputs.filter(o => o.operation_type === 'preprocess').length})</Tag>
                            </Radio.Button>
                            <Radio.Button value="detect_issues">
                              <Tag color="orange">问题检测 ({aiOutputs.filter(o => o.operation_type === 'detect_issues').length})</Tag>
                            </Radio.Button>
                          </Radio.Group>
                        </Space>
                        <Divider type="vertical" />
                        <Space size={8}>
                          <Text strong>执行状态:</Text>
                          <Radio.Group 
                            value={aiStatusFilter}
                            onChange={(e) => {
                              setAiStatusFilter(e.target.value);
                              // 状态过滤条件变化时重新加载（这里可以扩展API支持状态过滤）
                              if (aiOutputsLoaded) {
                                setAiCurrentPage(1);
                                // 注意：目前API可能不支持状态过滤，这里先保持原有的客户端过滤
                              }
                            }}
                            size="small"
                          >
                            <Radio.Button value="all">
                              全部
                            </Radio.Button>
                            <Radio.Button value="success">
                              <Tag color="green">成功 ({aiOutputs.filter(o => o.status === 'success').length})</Tag>
                            </Radio.Button>
                            <Radio.Button value="failed">
                              <Tag color="red">失败 ({aiOutputs.filter(o => o.status !== 'success').length})</Tag>
                            </Radio.Button>
                          </Radio.Group>
                        </Space>
                      </Space>
                    </Col>
                    <Col>
                      <Button
                        type="primary"
                        size="small"
                        icon={<SwapOutlined />}
                        loading={aiOutputsLoading}
                        onClick={() => loadAIOutputs(1, aiPageSize, true)}
                      >
                        手动刷新
                      </Button>
                    </Col>
                  </Row>
                </Card>

                <div className="ai-outputs-container">
                {aiOutputs
                  .filter(output => {
                    // 操作类型过滤
                    if (aiOutputFilter !== 'all' && output.operation_type !== aiOutputFilter) {
                      return false;
                    }
                    // 执行状态过滤
                    if (aiStatusFilter === 'success' && output.status !== 'success') {
                      return false;
                    }
                    if (aiStatusFilter === 'failed' && output.status === 'success') {
                      return false;
                    }
                    return true;
                  })
                  .map((output, index) => (
                  <Card 
                    key={output.id} 
                    className="ai-output-card"
                    style={{ marginBottom: 16 }}
                    title={
                      <Space>
                        <span>#{index + 1}</span>
                        <Tag color="blue">{output.operation_type}</Tag>
                        {output.section_title && (
                          <Text type="secondary">{output.section_title}</Text>
                        )}
                        <Tag color={output.status === 'success' ? 'green' : 'red'}>
                          {output.status === 'success' ? '成功' : '失败'}
                        </Tag>
                      </Space>
                    }
                    extra={
                      <Space>
                        {output.tokens_used && (
                          <Tag>Tokens: {output.tokens_used}</Tag>
                        )}
                        {output.processing_time && (
                          <Tag>耗时: {output.processing_time.toFixed(2)}s</Tag>
                        )}
                      </Space>
                    }
                  >
                    <Collapse ghost>
                      {/* 输入文本 */}
                      <Panel 
                        header={
                          <Space>
                            <FileTextOutlined />
                            <Text strong>输入文本 ({output.input_text.length} 字符)</Text>
                          </Space>
                        } 
                        key="input"
                      >
                        <div style={{ 
                          background: '#f0f2f5', 
                          padding: 12, 
                          borderRadius: 4,
                          maxHeight: 300,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          lineHeight: '1.6'
                        }}>
                          {formatInputText(output.input_text.substring(0, 1000))}
                          {output.input_text.length > 1000 && (
                            <div style={{ 
                              marginTop: 8, 
                              padding: 4, 
                              background: '#e6f7ff', 
                              borderRadius: 4,
                              fontSize: 11,
                              color: '#1890ff'
                            }}>
                              ... (显示前1000个字符，总长度: {output.input_text.length})
                            </div>
                          )}
                        </div>
                      </Panel>

                      {/* 原始输出 */}
                      <Panel 
                        header={
                          <Space>
                            <RobotOutlined />
                            <Text strong>模型原始输出</Text>
                          </Space>
                        } 
                        key="raw"
                      >
                        <div style={{ 
                          background: '#f6ffed', 
                          padding: 12, 
                          borderRadius: 4,
                          maxHeight: 400,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          lineHeight: '1.6'
                        }}>
                          {isLikelyJSON(output.raw_output) 
                            ? formatJSON(output.raw_output)
                            : decodeUnicode(output.raw_output)
                          }
                        </div>
                      </Panel>

                      {/* 解析后的结构化输出 */}
                      {output.parsed_output && (
                        <Panel 
                          header={
                            <Space>
                              <InfoCircleOutlined />
                              <Text strong>解析后的结构化数据</Text>
                            </Space>
                          } 
                          key="parsed"
                        >
                          <div style={{ 
                            background: '#fff', 
                            padding: 12, 
                            borderRadius: 4,
                            maxHeight: 400,
                            overflow: 'auto'
                          }}>
                            <pre style={{ 
                              margin: 0,
                              fontFamily: 'monospace',
                              fontSize: 12,
                              lineHeight: '1.6'
                            }}>
                              {decodeUnicode(JSON.stringify(output.parsed_output, null, 2))}
                            </pre>
                          </div>
                        </Panel>
                      )}

                      {/* 错误信息 */}
                      {output.error_message && (
                        <Panel 
                          header={
                            <Space>
                              <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                              <Text strong style={{ color: '#ff4d4f' }}>错误信息</Text>
                            </Space>
                          } 
                          key="error"
                        >
                          <Alert 
                            message={decodeUnicode(output.error_message)} 
                            type="error" 
                            showIcon 
                          />
                        </Panel>
                      )}
                    </Collapse>
                  </Card>
                ))}

                {/* AI输出分页器 */}
                {aiOutputs.length > 0 && (aiOutputs as any)._total && (
                  <div style={{ textAlign: 'center', marginTop: 24 }}>
                    <Pagination
                      current={aiCurrentPage}
                      pageSize={aiPageSize}
                      total={(aiOutputs as any)._total}
                      onChange={(page) => {
                        setAiCurrentPage(page);
                        loadAIOutputs(page, aiPageSize, true);
                      }}
                      showTotal={(total, range) => `${range[0]}-${range[1]} / ${total} 条AI输出`}
                      size="small"
                    />
                  </div>
                )}
                </div>
              </>
            )}
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default TaskDetailEnhanced;