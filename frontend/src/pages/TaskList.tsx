import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { usePageVisibility } from '../hooks/usePageVisibility';
import { useTaskList } from '../hooks/useTaskList';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import { 
  Card, Table, Button, Tag, Progress, Space, message, Popconfirm, 
  Badge, Tooltip, Dropdown, Menu, Input, Select, Row, Col, Statistic,
  Empty, Typography, Segmented, Pagination, Spin
} from 'antd';
import { 
  PlusOutlined, ReloadOutlined, DeleteOutlined, EyeOutlined,
  DownloadOutlined, FileTextOutlined, FilePdfOutlined, FileWordOutlined,
  FileMarkdownOutlined, FileUnknownOutlined, SearchOutlined,
  FilterOutlined, CheckCircleOutlined, CloseCircleOutlined,
  ClockCircleOutlined, SyncOutlined, ExclamationCircleOutlined,
  BarChartOutlined, ShareAltOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskAPI } from '../api';
import { Task, PaginationParams, PaginatedResponse } from '../types';
import { TaskShareModal } from '../components/TaskShareModal';
import './TaskList.css';

// 移除全局请求去重机制，改为组件级别的并发控制

const { Text } = Typography;
const { Option } = Select;

const TaskList: React.FC = () => {
  // 使用优化的任务列表Hook
  const {
    tasks,
    loading,
    loadingMore,
    isBackgroundRefreshing,
    currentPage,
    totalTasks,
    hasNextPage,
    searchText,
    statusFilter,
    setSearchText,
    setStatusFilter,
    loadTasks,
    loadMoreTasks,
    refreshTasks,
    backgroundRefresh,
    goToPage,
    statistics
  } = useTaskList({
    pageSize: 20,
    initialSearch: '',
    initialStatus: 'all'
  });

  // 其他UI状态
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');
  const [paginationMode, setPaginationMode] = useState<'infinite' | 'pagination'>('pagination'); // 默认使用分页模式
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // 分享模态框状态
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [shareTaskId, setShareTaskId] = useState<number | undefined>();
  const [shareTaskTitle, setShareTaskTitle] = useState<string | undefined>();
  
  const navigate = useNavigate();
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const pageSize = 20; // 与useTaskList中的pageSize保持一致
  
  // 使用优化的无限滚动Hook（仅在无限滚动模式时启用）
  const loadMoreTriggerRef = useInfiniteScroll({
    hasNextPage: paginationMode === 'infinite' ? hasNextPage : false, // 分页模式时禁用无限滚动
    loading: loadingMore,
    onLoadMore: loadMoreTasks,
    rootMargin: '50px', // 减小触发区域
    debounceMs: 1000 // 增加防抖时间
  });

  const handleDelete = useCallback(async (taskId: number) => {
    try {
      await taskAPI.deleteTask(taskId);
      message.success('任务已删除');
      // 刷新当前页数据
      setTimeout(() => refreshTasks(), 500);
    } catch (error) {
      message.error('删除任务失败');
    }
  }, [refreshTasks]);

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
      // 刷新当前页数据
      setTimeout(() => refreshTasks(), 1000);
    } catch (error) {
      message.error('批量删除失败');
    }
  }, [selectedRowKeys, refreshTasks]);

  const handleRetry = useCallback(async (taskId: number) => {
    try {
      await taskAPI.retryTask(taskId);
      message.success('任务已重新启动');
      // 刷新当前页数据
      setTimeout(() => refreshTasks(), 500);
    } catch (error) {
      message.error('重试失败');
    }
  }, [refreshTasks]);

  const handleDownloadReport = useCallback(async (taskId: number) => {
    try {
      await taskAPI.downloadReport(taskId);
      message.success('报告下载成功');
    } catch (error) {
      message.error('下载报告失败');
    }
  }, []);

  const handleDownloadFile = useCallback(async (taskId: number) => {
    try {
      const result = await taskAPI.downloadTaskFile(taskId);
      message.success(`原文件下载成功: ${result.filename}`);
    } catch (error: any) {
      console.error('下载文件失败:', error);
      if (error.response?.status === 404) {
        message.error('文件不存在或已被删除');
      } else if (error.response?.status === 403) {
        message.error('没有下载权限');
      } else {
        message.error('下载文件失败');
      }
    }
  }, []);

  const handleShare = useCallback((taskId: number, taskTitle?: string) => {
    setShareTaskId(taskId);
    setShareTaskTitle(taskTitle);
    setShareModalVisible(true);
  }, []);

  const handleShareSuccess = useCallback(() => {
    setShareModalVisible(false);
    setShareTaskId(undefined);
    setShareTaskTitle(undefined);
    message.success('任务分享成功！');
    // 可以选择刷新任务列表以显示分享状态
    setTimeout(() => refreshTasks(), 500);
  }, [refreshTasks]);

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

  // 统计数据已由useTaskList Hook提供

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
        const menuItems = [
          {
            key: 'view',
            icon: <EyeOutlined />,
            label: '查看详情',
            onClick: () => navigate(`/task/${record.id}`)
          },
          {
            key: 'download-file',
            icon: <FileTextOutlined />,
            label: '下载原文件',
            onClick: () => handleDownloadFile(record.id)
          },
          ...(record.status === 'completed' ? [{
            key: 'download',
            icon: <DownloadOutlined />,
            label: '下载报告',
            onClick: () => handleDownloadReport(record.id)
          }] : []),
          ...(record.status === 'failed' ? [{
            key: 'retry',
            icon: <ReloadOutlined />,
            label: '重试任务',
            onClick: () => handleRetry(record.id)
          }] : []),
          ...(record.status === 'completed' ? [{
            key: 'share',
            icon: <ShareAltOutlined />,
            label: '分享任务',
            onClick: () => handleShare(record.id, record.title || record.file_name)
          }] : []),
          { type: 'divider' as const },
          {
            key: 'delete',
            icon: <DeleteOutlined />,
            label: '删除任务',
            danger: true,
            onClick: () => handleDelete(record.id)
          }
        ];

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
            <Tooltip title="下载原文件">
              <Button
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => handleDownloadFile(record.id)}
              />
            </Tooltip>
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
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
              onClear={() => {
                console.log('🔍 搜索框已清空，恢复原有列表');
                setSearchText('');
              }}
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
            <Segmented
              className="pagination-mode-segmented"
              options={[
                { value: 'pagination', label: '分页' },
                { value: 'infinite', label: '滚动' },
              ]}
              value={paginationMode}
              onChange={(value) => {
                console.log('🔄 切换分页模式:', value);
                setPaginationMode(value as 'infinite' | 'pagination');
                // 切换模式时重新加载第1页数据
                setTimeout(() => {
                  refreshTasks();
                }, 100);
              }}
              style={{ marginLeft: '8px' }}
            />
            <Button
              className="action-button"
              icon={<ReloadOutlined />}
              onClick={() => {
                console.log('手动刷新按钮被点击');
                refreshTasks(); // 手动刷新显示loading，强制刷新
              }}
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
        <div className="task-table-container" ref={tableContainerRef}>
          <Table
            className="task-table"
            rowSelection={rowSelection}
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            loading={loading}
            pagination={false} // 关闭内置分页，使用无限滚动
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
          
          {/* 无限滚动加载更多触发器（仅无限滚动模式） */}
          {paginationMode === 'infinite' && hasNextPage && (
            <div 
              ref={loadMoreTriggerRef}
              style={{ 
                height: '50px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                padding: '20px',
                color: '#999',
                fontSize: '14px'
              }}
            >
              {loadingMore ? (
                <>
                  <SyncOutlined spin style={{ marginRight: '8px' }} />
                  正在加载更多...
                </>
              ) : (
                '向下滚动加载更多'
              )}
            </div>
          )}
          
          {/* 数据统计信息和分页导航 */}
          {!loading && tasks.length > 0 && (
            <div style={{ 
              textAlign: 'center', 
              padding: '20px', 
              borderTop: '1px solid #f0f0f0'
            }}>
              <div style={{ 
                color: '#999', 
                fontSize: '12px',
                marginBottom: '16px'
              }}>
                已显示 {tasks.length} / {totalTasks} 条记录
              </div>
              
              {/* 传统分页导航（仅分页模式时显示） */}
              {paginationMode === 'pagination' && totalTasks > pageSize && (
                <Pagination
                  current={currentPage}
                  pageSize={pageSize}
                  total={totalTasks}
                  showSizeChanger={false}
                  showQuickJumper={true}
                  showTotal={(total: number, range: [number, number]) => `${range[0]}-${range[1]} / ${total} 条`}
                  onChange={(page: number) => {
                    console.log('分页跳转到第', page, '页');
                    goToPage(page);
                  }}
                  size="small"
                  style={{ marginTop: '8px' }}
                />
              )}
            </div>
          )}
          
          {/* 无限滚动触发器（仅无限滚动模式） */}
          {paginationMode === 'infinite' && (
            <div ref={loadMoreTriggerRef} style={{ height: '20px', margin: '10px 0' }}>
              {loadingMore && (
                <div style={{ textAlign: 'center', padding: '10px' }}>
                  <Spin size="small" />
                  <span style={{ marginLeft: '8px' }}>加载更多...</span>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        tasks.length > 0 ? (
          <>
            <div className="task-cards-grid">
              {tasks.map(renderTaskCard)}
            </div>
            
            {/* 卡片视图的加载更多（仅无限滚动模式） */}
            {paginationMode === 'infinite' && hasNextPage && (
              <div 
                ref={loadMoreTriggerRef}
                style={{ 
                  height: '80px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  margin: '20px 0',
                  color: '#999',
                  fontSize: '14px'
                }}
              >
                {loadingMore ? (
                  <>
                    <SyncOutlined spin style={{ marginRight: '8px' }} />
                    正在加载更多任务...
                  </>
                ) : (
                  '向下滚动加载更多'
                )}
              </div>
            )}
            
            {/* 卡片视图数据统计和分页导航 */}
            {!loading && (
              <div style={{ 
                textAlign: 'center', 
                padding: '20px'
              }}>
                <div style={{ 
                  color: '#999', 
                  fontSize: '12px',
                  marginBottom: '16px'
                }}>
                  已显示 {tasks.length} / {totalTasks} 条记录
                </div>
                
                {/* 传统分页导航（仅分页模式时显示） */}
                {paginationMode === 'pagination' && totalTasks > pageSize && (
                  <Pagination
                    current={currentPage}
                    pageSize={pageSize}
                    total={totalTasks}
                    showSizeChanger={false}
                    showQuickJumper={true}
                    showTotal={(total: number, range: [number, number]) => `${range[0]}-${range[1]} / ${total} 条`}
                    onChange={(page: number) => {
                      console.log('分页跳转到第', page, '页');
                      goToPage(page);
                    }}
                    size="small"
                    style={{ marginTop: '8px' }}
                  />
                )}
              </div>
            )}
            
            {/* 卡片视图的无限滚动触发器（仅无限滚动模式） */}
            {paginationMode === 'infinite' && (
              <div ref={loadMoreTriggerRef} style={{ height: '20px', margin: '10px 0' }}>
                {loadingMore && (
                  <div style={{ textAlign: 'center', padding: '10px' }}>
                    <Spin size="small" />
                    <span style={{ marginLeft: '8px' }}>加载更多...</span>
                  </div>
                )}
              </div>
            )}
          </>
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
      
      {/* 任务分享模态框 */}
      <TaskShareModal
        visible={shareModalVisible}
        taskId={shareTaskId}
        taskTitle={shareTaskTitle}
        onCancel={() => setShareModalVisible(false)}
        onSuccess={handleShareSuccess}
      />
    </div>
  );
};

export default TaskList;