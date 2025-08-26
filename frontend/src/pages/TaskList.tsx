import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  Card, Table, Button, Tag, Progress, Space, message, Popconfirm, 
  Badge, Tooltip, Dropdown, Menu, Input, Select, Row, Col, Statistic,
  Empty, Typography, Segmented
} from 'antd';
import { 
  PlusOutlined, ReloadOutlined, DeleteOutlined, EyeOutlined,
  DownloadOutlined, FileTextOutlined, FilePdfOutlined, FileWordOutlined,
  FileMarkdownOutlined, FileUnknownOutlined, SearchOutlined,
  FilterOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, SyncOutlined, ExclamationCircleOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskAPI } from '../api';
import { Task } from '../types';
import './TaskList.css';

// 全局请求去重机制
let pendingTaskRequest: Promise<Task[]> | null = null;

const { Text } = Typography;
const { Option } = Select;

const TaskList: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [isBackgroundRefreshing, setIsBackgroundRefreshing] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState(0);
  const [isRequestPending, setIsRequestPending] = useState(false); // 防止并发请求
  const navigate = useNavigate();

  const loadTasks = useCallback(async (showLoading: boolean = true, forceRefresh: boolean = false) => {
    const now = Date.now();
    
    // 防止并发请求
    if (isRequestPending) {
      return;
    }
    
    // 防止频繁刷新，但允许强制刷新
    if (!forceRefresh && now - lastRefreshTime < 1000) {
      return;
    }
    
    setIsRequestPending(true);
    if (showLoading) {
      setLoading(true);
    }
    
    try {
      // 使用全局请求去重
      if (!pendingTaskRequest) {
        pendingTaskRequest = taskAPI.getTasks();
      }
      
      const data = await pendingTaskRequest;
      setTasks(data);
      setLastRefreshTime(now);
    } catch (error) {
      message.error('加载任务列表失败');
    } finally {
      pendingTaskRequest = null; // 清除请求状态
      setIsRequestPending(false);
      if (showLoading) {
        setLoading(false);
      }
    }
  }, []); // 移除lastRefreshTime依赖，避免循环

  // 后台静默刷新函数
  const backgroundRefresh = useCallback(async () => {
    // 防止并发请求
    if (isRequestPending) {
      return;
    }
    
    const now = Date.now();
    // 防止频繁刷新
    if (now - lastRefreshTime < 2000) { // 增加到2秒间隔
      return;
    }
    
    setIsRequestPending(true);
    setIsBackgroundRefreshing(true);
    
    try {
      // 使用全局请求去重
      if (!pendingTaskRequest) {
        pendingTaskRequest = taskAPI.getTasks();
      }
      
      const data = await pendingTaskRequest;
      setTasks(data);
      setLastRefreshTime(now);
    } catch (error) {
      // 后台刷新失败时不显示错误信息，避免干扰用户
      if (process.env.NODE_ENV === 'development') {
        console.warn('后台刷新失败:', error);
      }
    } finally {
      pendingTaskRequest = null; // 清除请求状态
      setIsRequestPending(false);
      setTimeout(() => setIsBackgroundRefreshing(false), 1000);
    }
  }, []); // 移除依赖，避免循环

  useEffect(() => {
    // 立即加载任务，并在页面可见时刷新
    loadTasks(true, true);
    
    // 监听页面可见性变化，在页面重新可见时刷新数据
    let visibilityTimeout: NodeJS.Timeout | null = null;
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // 防止频繁触发，延迟刷新
        if (visibilityTimeout) {
          clearTimeout(visibilityTimeout);
        }
        visibilityTimeout = setTimeout(() => {
          loadTasks(false, true);
        }, 1000); // 延迟1秒刷新
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []); // 只在组件挂载时加载一次

  useEffect(() => {
    // 智能刷新：根据任务状态动态调整刷新频率
    const hasProcessingTasks = tasks.some(task => 
      task.status === 'processing' || task.status === 'pending'
    );
    const interval = hasProcessingTasks ? 5000 : 15000; // 增加刷新间隔
    
    const timer = setInterval(() => {
      backgroundRefresh();
    }, interval);
    
    // 清理定时器
    return () => {
      clearInterval(timer);
    };
  }, [backgroundRefresh, tasks.filter(t => t.status === 'processing' || t.status === 'pending').length]); // 优化依赖，只关注处理中任务数量

  // 使用 useMemo 优化过滤逻辑，避免不必要的重新计算
  const filteredTasks = useMemo(() => {
    let filtered = [...tasks];
    
    // 搜索过滤
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      filtered = filtered.filter(task => 
        task.title?.toLowerCase().includes(searchLower) ||
        task.file_name.toLowerCase().includes(searchLower)
      );
    }
    
    // 状态过滤
    if (statusFilter !== 'all') {
      filtered = filtered.filter(task => task.status === statusFilter);
    }
    
    return filtered;
  }, [tasks, searchText, statusFilter]);

  const handleDelete = useCallback(async (taskId: number) => {
    try {
      await taskAPI.deleteTask(taskId);
      message.success('任务已删除');
      // 延迟刷新，避免立即请求
      setTimeout(() => backgroundRefresh(), 500);
    } catch (error) {
      message.error('删除任务失败');
    }
  }, [backgroundRefresh]);

  const handleBatchDelete = useCallback(async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的任务');
      return;
    }
    
    try {
      // 批量删除（需要后端支持）
      for (const taskId of selectedRowKeys) {
        await taskAPI.deleteTask(Number(taskId));
      }
      message.success(`成功删除 ${selectedRowKeys.length} 个任务`);
      setSelectedRowKeys([]);
      // 延迟刷新，避免立即请求
      setTimeout(() => backgroundRefresh(), 1000);
    } catch (error) {
      message.error('批量删除失败');
    }
  }, [selectedRowKeys, backgroundRefresh]);

  const handleRetry = useCallback(async (taskId: number) => {
    try {
      await taskAPI.retryTask(taskId);
      message.success('任务已重新启动');
      // 延迟刷新，避免立即请求
      setTimeout(() => backgroundRefresh(), 500);
    } catch (error) {
      message.error('重试失败');
    }
  }, [backgroundRefresh]);

  const handleDownloadReport = useCallback(async (taskId: number) => {
    try {
      await taskAPI.downloadReport(taskId);
      message.success('报告下载成功');
    } catch (error) {
      message.error('下载报告失败');
    }
  }, []);

  const getStatusTag = (status: string) => {
    const statusMap: { [key: string]: { color: string; text: string; icon: React.ReactNode } } = {
      pending: { color: 'default', text: '等待中', icon: <ClockCircleOutlined /> },
      processing: { color: 'processing', text: '处理中', icon: <SyncOutlined spin /> },
      completed: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', text: '失败', icon: <CloseCircleOutlined /> },
    };
    const config = statusMap[status] || statusMap.pending;
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return <FilePdfOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />;
      case 'doc':
      case 'docx':
        return <FileWordOutlined style={{ color: '#1890ff', fontSize: 16 }} />;
      case 'md':
        return <FileMarkdownOutlined style={{ color: '#52c41a', fontSize: 16 }} />;
      case 'txt':
        return <FileTextOutlined style={{ color: '#722ed1', fontSize: 16 }} />;
      default:
        return <FileUnknownOutlined style={{ color: '#8c8c8c', fontSize: 16 }} />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 使用 useMemo 优化统计数据计算，避免每次渲染时重新计算
  const statistics = useMemo(() => {
    return {
      total: tasks.length,
      pending: tasks.filter(t => t.status === 'pending').length,
      processing: tasks.filter(t => t.status === 'processing').length,
      completed: tasks.filter(t => t.status === 'completed').length,
      failed: tasks.filter(t => t.status === 'failed').length,
    };
  }, [tasks]);

  const formatTime = (seconds?: number) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${Math.round(seconds)}秒`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}分${secs}秒`;
  };

  const calculateActualProcessingTime = useCallback((record: Task) => {
    // 计算基于时间戳的实际耗时（作为基准）
    let actualTimeFromTimestamps = null;
    if (record.status === 'completed' && record.completed_at && record.created_at) {
      const startTime = new Date(record.created_at + 'Z').getTime(); // 明确指定UTC
      const endTime = new Date(record.completed_at + 'Z').getTime(); // 明确指定UTC
      actualTimeFromTimestamps = (endTime - startTime) / 1000;
    }
    
    // 如果存储的processing_time与实际时间差异过大（超过1小时或者相差8小时左右），
    // 则认为processing_time可能存在时区计算错误，使用实际时间计算
    if (record.processing_time && actualTimeFromTimestamps) {
      const timeDiff = Math.abs(record.processing_time - actualTimeFromTimestamps);
      const eightHours = 8 * 3600; // 8小时的秒数
      
      // 如果时间差接近8小时（时区错误）或超过1小时（异常），使用实际计算时间
      if (timeDiff > 3600 && (Math.abs(timeDiff - eightHours) < 300 || timeDiff > eightHours)) {
        console.warn(`任务${record.id}存在时区计算错误，使用实际时间。存储时间：${record.processing_time}s，实际时间：${actualTimeFromTimestamps}s`);
        return actualTimeFromTimestamps;
      }
      
      // 否则使用存储的processing_time
      return record.processing_time;
    }
    
    // 如果只有processing_time，直接使用
    if (record.processing_time) {
      return record.processing_time;
    }
    
    // 如果只能通过时间戳计算，使用实际计算时间
    if (actualTimeFromTimestamps) {
      return actualTimeFromTimestamps;
    }
    
    return null;
  }, []);

  const formatChars = (chars?: number) => {
    if (!chars) return '-';
    if (chars < 1000) return `${chars}字`;
    if (chars < 10000) return `${(chars / 1000).toFixed(1)}千字`;
    return `${(chars / 10000).toFixed(1)}万字`;
  };

  const columns = [
    {
      title: '文件信息',
      key: 'file',
      width: '30%',
      render: (_: any, record: Task) => (
        <Space>
          {getFileIcon(record.file_name)}
          <div>
            <div style={{ fontWeight: 500 }}>{record.title || record.file_name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.file_name} · {formatFileSize(record.file_size || 0)}
            </Text>
            {record.document_chars && (
              <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                字符数: {formatChars(record.document_chars)}
              </Text>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: '创建人',
      key: 'creator',
      width: '10%',
      render: (_: any, record: Task) => {
        // 显示真实的创建人名称，不显示系统用户
        const creatorName = record.created_by_name || '未知用户';
        let creatorType = '普通用户'; // 默认值
        
        if (record.created_by_type === 'system_admin') {
          creatorType = '系统管理员';
        } else if (record.created_by_type === 'admin') {
          creatorType = '系统管理员'; // 管理员也显示为系统管理员
        } else if (record.created_by_type === 'normal_user') {
          creatorType = '普通用户';
        }
        
        return (
          <div>
            <div style={{ fontWeight: 500, fontSize: 13 }}>
              {creatorName}
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {creatorType}
            </Text>
          </div>
        );
      },
    },
    {
      title: '模型',
      key: 'model',
      width: '13%',
      render: (_: any, record: Task) => (
        record.ai_model_label ? (
          <Tooltip title={record.ai_model_label}>
            <Tag color="blue" style={{ fontSize: 11 }}>
              {record.ai_model_label.length > 10 
                ? record.ai_model_label.substring(0, 10) + '...' 
                : record.ai_model_label}
            </Tag>
          </Tooltip>
        ) : '-'
      ),
    },
    {
      title: '状态',
      key: 'status_progress',
      width: '15%',
      render: (_: any, record: Task) => (
        <div>
          <div style={{ marginBottom: 8 }}>
            {getStatusTag(record.status)}
          </div>
          {record.status === 'completed' ? (
            <div>
              {(() => {
                const actualTime = calculateActualProcessingTime(record);
                return actualTime && (
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    耗时: {formatTime(actualTime)}
                  </div>
                );
              })()}
              {record.completed_at && (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  完成: {new Date(record.completed_at + 'Z').toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  })} (本地时间)
                </div>
              )}
            </div>
          ) : record.status === 'failed' ? (
            <div style={{ fontSize: 11, color: '#ff4d4f', marginTop: 2 }}>
              {record.error_message ? `错误: ${record.error_message.substring(0, 30)}...` : '处理失败'}
            </div>
          ) : record.status === 'processing' ? (
            <div>
              <Progress 
                percent={Math.round(record.progress)} 
                size="small"
                strokeColor="#1890ff"
                format={(percent) => `${percent}%`}
              />
              <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 2 }}>
                正在处理中...
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 2 }}>
              等待处理
            </div>
          )}
        </div>
      ),
      filters: [
        { text: '等待中', value: 'pending' },
        { text: '处理中', value: 'processing' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
      ],
      onFilter: (value: any, record: Task) => record.status === value,
    },
    {
      title: '问题统计',
      key: 'issue_stats',
      width: '15%',
      render: (_: any, record: Task) => (
        <div>
          {record.status === 'completed' ? (
            <div>
              {record.issue_count !== undefined ? (
                <div>
                  <div style={{ fontSize: 12, color: '#262626', fontWeight: 500 }}>
                    发现 {record.issue_count} 个问题
                  </div>
                  {record.processed_issues !== undefined && (
                    <div style={{ fontSize: 11, color: '#52c41a', marginTop: 2 }}>
                      已处理: {record.processed_issues}
                    </div>
                  )}
                  {/* 问题处理进度条 */}
                  {record.issue_count > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <Progress 
                        percent={record.processed_issues ? Math.round((record.processed_issues / record.issue_count) * 100) : 0} 
                        size="small"
                        strokeColor="#52c41a"
                        trailColor="#f0f0f0"
                        format={(percent) => `${percent}%`}
                        style={{ fontSize: 10 }}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  无问题数据
                </div>
              )}
            </div>
          ) : record.status === 'processing' ? (
            <div>
              {record.issue_count !== undefined && record.issue_count > 0 ? (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  预计发现 {record.issue_count} 个问题
                </div>
              ) : (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  分析中...
                </div>
              )}
            </div>
          ) : record.status === 'pending' ? (
            <div>
              {record.issue_count !== undefined && record.issue_count > 0 ? (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  上次: {record.issue_count} 个问题
                </div>
              ) : (
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  待分析
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: '#8c8c8c' }}>
              -
            </div>
          )}
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '10%',
      render: (date: string) => (
        <Tooltip title={new Date(date + 'Z').toLocaleString('zh-CN') + ' (本地时间)'}>
          <Text style={{ fontSize: 12 }}>
            {new Date(date + 'Z').toLocaleDateString('zh-CN')}
          </Text>
        </Tooltip>
      ),
      sorter: (a: Task, b: Task) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: any, record: Task) => {
        const menu = (
          <Menu>
            <Menu.Item key="view" icon={<EyeOutlined />} onClick={() => navigate(`/task/${record.id}`)}>
              查看详情
            </Menu.Item>
            {record.status === 'completed' && (
              <Menu.Item key="download" icon={<DownloadOutlined />} onClick={() => handleDownloadReport(record.id)}>
                下载报告
              </Menu.Item>
            )}
            {record.status === 'failed' && (
              <Menu.Item key="retry" icon={<ReloadOutlined />} onClick={() => handleRetry(record.id)}>
                重试任务
              </Menu.Item>
            )}
            <Menu.Divider />
            <Menu.Item key="delete" icon={<DeleteOutlined />} danger onClick={() => handleDelete(record.id)}>
              删除任务
            </Menu.Item>
          </Menu>
        );

        return (
          <Space size="small">
            <Button
              type="primary"
              size="small"
              ghost
              icon={<EyeOutlined />}
              onClick={() => navigate(`/task/${record.id}`)}
            >
              查看
            </Button>
            <Dropdown overlay={menu} trigger={['click']}>
              <Button size="small">
                更多 <FilterOutlined />
              </Button>
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  const getStatusText = (status: string) => {
    const statusMap: { [key: string]: string } = {
      pending: '等待中',
      processing: '处理中',
      completed: '已完成',
      failed: '失败',
    };
    return statusMap[status] || '未知';
  };

  const renderTaskCard = (task: Task) => (
    <Card
      key={task.id}
      className="task-card-item"
      onClick={() => navigate(`/task/${task.id}`)}
      title={
        <div className="task-card-header">
          <h3 className="task-card-title">{task.title || task.file_name}</h3>
          <div className="task-card-meta">
            {getFileIcon(task.file_name)}
            <Tag className={`status-tag status-${task.status}`}>
              {getStatusText(task.status)}
            </Tag>
          </div>
        </div>
      }
    >
      <div className="task-card-body">
        {task.status === 'processing' && (
          <div className="task-progress-section">
            <div className="task-progress-label">
              <span>处理进度</span>
              <span>{Math.round(task.progress)}%</span>
            </div>
            <Progress percent={Math.round(task.progress)} strokeColor="#74b9ff" />
          </div>
        )}
        
        <div className="task-info-grid">
          <div className="task-info-item">
            <div className="task-info-label">文件大小</div>
            <div className="task-info-value">{formatFileSize(task.file_size || 0)}</div>
          </div>
          <div className="task-info-item">
            <div className="task-info-label">创建时间</div>
            <div className="task-info-value">{new Date(task.created_at + 'Z').toLocaleDateString('zh-CN')}</div>
          </div>
          {task.document_chars && (
            <div className="task-info-item">
              <div className="task-info-label">文档字符</div>
              <div className="task-info-value">{formatChars(task.document_chars)}</div>
            </div>
          )}
          {task.status === 'completed' && task.issue_count !== undefined && (
            <div className="task-info-item">
              <div className="task-info-label">发现问题</div>
              <div className="task-info-value">
                {task.issue_count} 个
                {task.processed_issues !== undefined && (
                  <div style={{ fontSize: 10, color: '#52c41a', marginTop: 2 }}>
                    已处理: {task.processed_issues}
                  </div>
                )}
              </div>
            </div>
          )}
          {/* 问题处理进度 - 仅在已完成且有问题时显示 */}
          {task.status === 'completed' && task.issue_count !== undefined && task.issue_count > 0 && (
            <div className="task-info-item" style={{ gridColumn: 'span 2' }}>
              <div className="task-info-label">处理进度</div>
              <div className="task-info-value" style={{ width: '100%' }}>
                <Progress 
                  percent={task.processed_issues ? Math.round((task.processed_issues / task.issue_count) * 100) : 0} 
                  size="small"
                  strokeColor="#52c41a"
                  trailColor="#f0f0f0"
                  format={(percent) => `${percent}%`}
                  style={{ fontSize: 10 }}
                />
                <div style={{ fontSize: 10, color: '#8c8c8c', marginTop: 2 }}>
                  {task.processed_issues || 0}/{task.issue_count} 已处理
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="task-actions">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/task/${task.id}`);
            }}
          >
            查看
          </Button>
          {task.status === 'completed' && (
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleDownloadReport(task.id);
              }}
            >
              报告
            </Button>
          )}
          {task.status === 'failed' && (
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleRetry(task.id);
              }}
            >
              重试
            </Button>
          )}
          <Popconfirm
            title="确定删除该任务吗？"
            onConfirm={() => {
              handleDelete(task.id);
            }}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            >
              删除
            </Button>
          </Popconfirm>
        </div>
      </div>
    </Card>
  );

  return (
    <div className="task-list-container">
      {/* 页面标题 */}
      <div className="task-list-header">
        <h1 className="task-list-title">任务管理中心</h1>
        <p style={{ margin: '8px 0 0 0', color: '#64748b' }}>
          智能文档检测，全流程任务管理
        </p>
        
        {/* 统计卡片 */}
        <Row gutter={[16, 16]} className="task-stats-row">
          <Col xs={24} sm={12} md={4}>
            <Card className="task-stat-card">
              <FileTextOutlined className="stat-icon total" />
              <Statistic
                title="总任务数"
                value={statistics.total}
                valueStyle={{ color: '#1890ff', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Card className="task-stat-card">
              <ClockCircleOutlined className="stat-icon pending" style={{ color: '#faad14' }} />
              <Statistic
                title="等待中"
                value={statistics.pending}
                valueStyle={{ color: '#faad14', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Card className="task-stat-card">
              <SyncOutlined spin className="stat-icon processing" style={{ color: '#1890ff' }} />
              <Statistic
                title="处理中"
                value={statistics.processing}
                valueStyle={{ color: '#1890ff', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Card className="task-stat-card">
              <CheckCircleOutlined className="stat-icon completed" />
              <Statistic
                title="已完成"
                value={statistics.completed}
                valueStyle={{ color: '#52c41a', fontWeight: 700 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={5}>
            <Card className="task-stat-card">
              <CloseCircleOutlined className="stat-icon failed" />
              <Statistic
                title="失败"
                value={statistics.failed}
                valueStyle={{ color: '#f5222d', fontWeight: 700 }}
              />
            </Card>
          </Col>
        </Row>
      </div>

      {/* 控制面板 */}
      <div className="task-controls">
        <div className="task-controls-row">
          <div className="task-controls-left">
            <Input
              className="search-input"
              placeholder="搜索文件名或标题..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
            <Select
              className="filter-select"
              placeholder="状态筛选"
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Option value="all">全部状态</Option>
              <Option value="pending">等待中</Option>
              <Option value="processing">处理中</Option>
              <Option value="completed">已完成</Option>
              <Option value="failed">失败</Option>
            </Select>
          </div>
          <div className="task-controls-right">
            {/* 后台刷新指示器 */}
            {isBackgroundRefreshing && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                marginRight: '8px',
                fontSize: '12px',
                color: '#1890ff'
              }}>
                <SyncOutlined spin style={{ marginRight: '4px' }} />
                更新中...
              </div>
            )}
            <Segmented
              className="view-mode-segmented"
              options={[
                { value: 'table', icon: <FilterOutlined />, label: '表格' },
                { value: 'card', icon: <BarChartOutlined />, label: '卡片' },
              ]}
              value={viewMode}
              onChange={(value) => setViewMode(value as 'table' | 'card')}
            />
            <Button
              className="action-button"
              icon={<ReloadOutlined />}
              onClick={() => loadTasks(true, true)} // 手动刷新显示loading，强制刷新
              loading={loading}
            >
              刷新
            </Button>
            <Button
              className="action-button primary"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/create')}
            >
              新建任务
            </Button>
          </div>
        </div>
      </div>

      {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <div className="batch-actions-bar">
          <div className="batch-actions-info">
            已选择 <strong>{selectedRowKeys.length}</strong> 个任务
          </div>
          <div className="batch-actions-buttons">
            <Button onClick={() => setSelectedRowKeys([])}>
              取消选择
            </Button>
            <Popconfirm
              title={`确定删除选中的 ${selectedRowKeys.length} 个任务吗？`}
              onConfirm={handleBatchDelete}
              okText="确定"
              cancelText="取消"
            >
              <Button danger icon={<DeleteOutlined />}>
                批量删除
              </Button>
            </Popconfirm>
          </div>
        </div>
      )}

      {/* 主内容区域 */}
      {viewMode === 'table' ? (
        <div className="task-table-container">
          <Table
            className="task-table"
            rowSelection={rowSelection}
            columns={columns}
            dataSource={filteredTasks}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条记录`,
              showQuickJumper: true,
            }}
            locale={{
              emptyText: (
                <div className="empty-state">
                  <FileTextOutlined className="empty-icon" />
                  <div className="empty-title">暂无任务</div>
                  <div className="empty-description">点击"新建任务"开始您的文档检测之旅</div>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => navigate('/create')}
                  >
                    立即创建
                  </Button>
                </div>
              )
            }}
          />
        </div>
      ) : (
        filteredTasks.length > 0 ? (
          <div className="task-cards-grid">
            {filteredTasks.map(renderTaskCard)}
          </div>
        ) : (
          <div className="empty-state">
            <FileTextOutlined className="empty-icon" />
            <div className="empty-title">暂无任务</div>
            <div className="empty-description">点击"新建任务"开始您的文档检测之旅</div>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/create')}
            >
              立即创建
            </Button>
          </div>
        )
      )}
    </div>
  );
};

export default TaskList;