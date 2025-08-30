import React, { useState, useEffect, useMemo } from 'react';
import { 
  Row, 
  Col, 
  Spin, 
  Alert, 
  Typography, 
  Card, 
  Space,
  message,
  BackTop
} from 'antd';
import { 
  DashboardOutlined, 
  ReloadOutlined 
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import OperationsTimeRangeSelector from '../components/OperationsTimeRangeSelector';
import {
  TaskStatisticsCard,
  UserStatisticsCard,
  IssueStatisticsCard,
  FeedbackStatisticsCard,
  TokenStatisticsCard,
} from '../components/OperationsStatisticsCard';
import CriticalIssuesList from '../components/CriticalIssuesList';
import { operationsService } from '../services/operationsService';
import type { OperationsOverview } from '../types/operations';
import type { TimeRangeType } from '../components/OperationsTimeRangeSelector';

const { Title, Text } = Typography;

const OperationsOverviewPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRangeType>({ type: '30days' });
  const [lastRefreshTime, setLastRefreshTime] = useState<Date>(new Date());

  // 缓存默认数据，避免每次渲染创建新对象
  const defaultTasksData = useMemo(() => ({
    total: 0, running: 0, completed: 0, failed: 0, success_rate: 0,
    today_total: 0, today_completed: 0, today_failed: 0
  }), []);

  const defaultUsersData = useMemo(() => ({
    total_users: 0, active_users: 0, new_registrations: 0,
    today_active: 0, today_new_registrations: 0, current_online: 0
  }), []);

  const defaultIssuesData = useMemo(() => ({
    total_issues: 0, new_issues: 0, accepted_issues: 0, rejected_issues: 0,
    pending_issues: 0, critical_issues: 0, high_issues: 0, medium_issues: 0,
    low_issues: 0, today_new: 0, today_accepted: 0
  }), []);

  const defaultFeedbackData = useMemo(() => ({
    total_feedback: 0, valid_feedback: 0, average_score: 0,
    score_distribution: {}, today_feedback: 0, today_average_score: 0
  }), []);

  const defaultTokensData = useMemo(() => ({
    total_tokens: 0, input_tokens: 0, output_tokens: 0, estimated_cost: 0,
    today_tokens: 0, today_cost: 0, by_model: {}
  }), []);

  // 使用React Query进行数据获取和缓存管理
  const {
    data: operationsData,
    isLoading,
    error,
    refetch,
    isFetching
  } = useQuery<OperationsOverview, Error>({
    queryKey: ['operations-overview', timeRange],
    queryFn: async () => {
      const params = {
        time_range_type: timeRange.type,
        start_date: timeRange.start_date,
        end_date: timeRange.end_date,
        include_trends: true,
        include_critical_issues: true,
        max_critical_issues: 20,
      };

      const startTime = performance.now();
      const data = await operationsService.getOperationsOverview(params);
      const endTime = performance.now();
      const loadTime = Math.round(endTime - startTime);

      console.log(`运营数据加载完成，耗时: ${loadTime}ms`);
      
      if (loadTime > 1000) {
        message.warning(`数据加载较慢 (${loadTime}ms)，建议检查网络或服务器性能`);
      }

      setLastRefreshTime(new Date());
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5分钟内认为数据是新鲜的
    gcTime: 15 * 60 * 1000, // 缓存15分钟
    refetchOnWindowFocus: false, // 窗口聚焦时不自动刷新
    retry: 2, // 最多重试2次
  });

  const handleTimeRangeChange = (newTimeRange: TimeRangeType) => {
    setTimeRange(newTimeRange);
  };

  const handleRefresh = () => {
    refetch();
  };

  const handleViewIssue = (issueId: number, taskId: number) => {
    // 这里可以跳转到问题详情页面
    window.open(`/tasks/${taskId}#issue-${issueId}`, '_blank');
  };

  // 错误处理
  if (error) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="加载运营数据失败"
          description={error instanceof Error ? error.message : '未知错误'}
          type="error"
          action={
            <div>
              <Space>
                <button onClick={handleRefresh}>
                  <ReloadOutlined /> 重试
                </button>
              </Space>
            </div>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '24px', 
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)', 
      minHeight: '100vh' 
    }}>
      <div style={{ 
        marginBottom: 32,
        background: 'rgba(255, 255, 255, 0.9)',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)'
      }}>
        <Space align="baseline" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={2} style={{ 
            margin: 0,
            background: 'linear-gradient(135deg, #1890ff, #722ed1)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent',
            fontWeight: 'bold'
          }}>
            <DashboardOutlined style={{ color: '#1890ff', marginRight: '8px' }} />
            运营总览
          </Title>
          <Space>
            <Text type="secondary" style={{ fontSize: '13px' }}>
              📈 最后更新: {lastRefreshTime.toLocaleTimeString()}
            </Text>
            {isFetching && (
              <Text type="secondary" style={{ fontSize: '13px' }}>
                <Spin size="small" /> 数据刷新中...
              </Text>
            )}
          </Space>
        </Space>
      </div>

      <Card style={{ 
        marginBottom: 32,
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
        border: 'none'
      }}>
        <OperationsTimeRangeSelector
          value={timeRange}
          onChange={handleTimeRangeChange}
          loading={isLoading}
        />
      </Card>

      <Spin spinning={isLoading} tip="🚀 正在加载运营数据...">
        <div style={{
          background: 'rgba(255, 255, 255, 0.3)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '32px',
          backdropFilter: 'blur(10px)'
        }}>
          <Title level={3} style={{ 
            textAlign: 'center', 
            marginBottom: '24px',
            color: '#595959',
            fontWeight: 500
          }}>
            📊 核心数据概览
          </Title>
          
          {/* 第一行：任务统计、用户统计、问题统计 */}
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={8}>
              <div style={{
                transform: isLoading ? 'scale(0.98)' : 'scale(1)',
                transition: 'all 0.3s ease',
                filter: isLoading ? 'blur(2px)' : 'none'
              }}>
                <TaskStatisticsCard 
                  data={operationsData?.tasks || defaultTasksData}
                  loading={isLoading}
                />
              </div>
            </Col>
            
            <Col xs={24} lg={8}>
              <div style={{
                transform: isLoading ? 'scale(0.98)' : 'scale(1)',
                transition: 'all 0.3s ease',
                filter: isLoading ? 'blur(2px)' : 'none'
              }}>
                <UserStatisticsCard 
                  data={operationsData?.users || defaultUsersData}
                  trends={operationsData?.trends?.user_trends || []}
                  loading={isLoading}
                />
              </div>
            </Col>

            <Col xs={24} lg={8}>
              <div style={{
                transform: isLoading ? 'scale(0.98)' : 'scale(1)',
                transition: 'all 0.3s ease',
                filter: isLoading ? 'blur(2px)' : 'none'
              }}>
                <IssueStatisticsCard 
                  data={operationsData?.issues || defaultIssuesData}
                  loading={isLoading}
                />
              </div>
            </Col>
          </Row>
        </div>

        <div style={{
          background: 'rgba(255, 255, 255, 0.3)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '32px',
          backdropFilter: 'blur(10px)'
        }}>
          <Title level={3} style={{ 
            textAlign: 'center', 
            marginBottom: '24px',
            color: '#595959',
            fontWeight: 500
          }}>
            💬 反馈与成本分析
          </Title>
          
          {/* 第二行：反馈统计、Token消耗 */}
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <div style={{
                transform: isLoading ? 'scale(0.98)' : 'scale(1)',
                transition: 'all 0.3s ease',
                filter: isLoading ? 'blur(2px)' : 'none'
              }}>
                <FeedbackStatisticsCard 
                  data={operationsData?.feedback || defaultFeedbackData}
                  loading={isLoading}
                />
              </div>
            </Col>

            <Col xs={24} lg={12}>
              <div style={{
                transform: isLoading ? 'scale(0.98)' : 'scale(1)',
                transition: 'all 0.3s ease',
                filter: isLoading ? 'blur(2px)' : 'none'
              }}>
                <TokenStatisticsCard 
                  data={operationsData?.tokens || defaultTokensData}
                  loading={isLoading}
                />
              </div>
            </Col>
          </Row>
        </div>

        {/* 关键问题列表 */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.3)',
          borderRadius: '16px',
          padding: '24px',
          backdropFilter: 'blur(10px)'
        }}>
          <Title level={3} style={{ 
            textAlign: 'center', 
            marginBottom: '24px',
            color: '#595959',
            fontWeight: 500
          }}>
            🚨 关键问题追踪
          </Title>
          
          <div style={{
            transform: isLoading ? 'scale(0.98)' : 'scale(1)',
            transition: 'all 0.3s ease',
            filter: isLoading ? 'blur(2px)' : 'none'
          }}>
            <CriticalIssuesList
              issues={operationsData?.critical_issues || []}
              loading={isLoading}
              onViewIssue={handleViewIssue}
              maxHeight={500}
            />
          </div>
        </div>
      </Spin>

      <BackTop />
    </div>
  );
};

export default OperationsOverviewPage;