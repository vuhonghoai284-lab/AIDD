import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  Spin,
  message,
  Tabs,
  Progress,
  Table,
  Typography,
  Space,
  Tag,
  Button
} from 'antd';
import {
  UserOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  BugOutlined,
  ReloadOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { analyticsAPI } from '../api';
import {
  AnalyticsData,
  UserStats,
  TaskStats,
  SystemStats,
  IssueStats,
  ErrorStats,
  TrendData,
  DistributionData
} from '../types';
import './Analytics.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

// 格式化字节大小
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化处理时间
const formatProcessingTime = (seconds?: number): string => {
  if (!seconds) return '--';
  if (seconds < 60) return `${seconds.toFixed(1)}秒`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds.toFixed(0)}秒`;
};

// 大型统计卡片组件
const BigStatCard: React.FC<{
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color?: string;
  suffix?: string;
  trend?: { value: number; isIncrease: boolean };
  description?: string;
}> = ({ title, value, icon, color = '#1890ff', suffix, trend, description }) => (
  <Card className="big-stat-card" hoverable style={{ textAlign: 'center' }}>
    <div style={{ padding: '16px 0' }}>
      <div className="big-stat-icon" style={{ 
        color, 
        fontSize: '48px',
        marginBottom: '16px',
        display: 'block'
      }}>
        {icon}
      </div>
      <Statistic
        title={title}
        value={value}
        suffix={suffix}
        valueStyle={{ 
          color, 
          fontSize: '32px', 
          fontWeight: '800',
          marginBottom: '8px'
        }}
      />
      {trend && (
        <div style={{ 
          fontSize: '14px', 
          color: trend.isIncrease ? '#52c41a' : '#f5222d',
          marginTop: '8px'
        }}>
          {trend.isIncrease ? '↗' : '↘'} {Math.abs(trend.value)}%
        </div>
      )}
      {description && (
        <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginTop: '4px' }}>
          {description}
        </Text>
      )}
    </div>
  </Card>
);

// 统计卡片组件
const StatCard: React.FC<{
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color?: string;
  suffix?: string;
}> = ({ title, value, icon, color = '#1890ff', suffix }) => (
  <Card className="stat-card" hoverable>
    <div className="stat-content">
      <div className="stat-icon" style={{ color, fontSize: '32px' }}>
        {icon}
      </div>
      <div className="stat-info">
        <Statistic
          title={title}
          value={value}
          suffix={suffix}
          valueStyle={{ color, fontSize: '20px', fontWeight: 'bold' }}
        />
      </div>
    </div>
  </Card>
);

// 趋势图表组件（简化实现）
const TrendChart: React.FC<{
  data: TrendData[];
  title: string;
}> = ({ data, title }) => {
  const maxValue = Math.max(...data.map(d => d.count));
  
  return (
    <div className="trend-chart">
      <Title level={5}>{title}</Title>
      <div className="chart-container">
        {data.slice(-7).map((item, index) => (
          <div key={index} className="chart-bar">
            <div
              className="bar"
              style={{
                height: `${maxValue > 0 ? (item.count / maxValue) * 100 : 0}%`,
                backgroundColor: '#1890ff'
              }}
            />
            <div className="bar-label">
              {new Date(item.date).toLocaleDateString('zh-CN', {
                month: 'numeric',
                day: 'numeric'
              })}
            </div>
            <div className="bar-value">{item.count}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 分布饼图组件（简化实现）
const PieChart: React.FC<{
  data: DistributionData[];
  title: string;
  nameKey: string;
}> = ({ data, title, nameKey }) => {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#fa8c16'];
  
  return (
    <div className="pie-chart">
      <Title level={5}>{title}</Title>
      <div className="chart-legend">
        {data.map((item, index) => (
          <div key={index} className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: colors[index % colors.length] }}
            />
            <span>{item[nameKey]}: {item.count} ({total > 0 ? ((item.count / total) * 100).toFixed(1) : 0}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const Analytics: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');

  const loadData = async () => {
    setLoading(true);
    try {
      const analyticsData = await analyticsAPI.getOverview(days);
      setData(analyticsData);
    } catch (error) {
      message.error('获取运营数据失败');
      console.error('Analytics data fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days]);

  const handleRefresh = () => {
    loadData();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载运营数据中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Text>暂无数据</Text>
      </div>
    );
  }

  // 最近错误列表列定义
  const errorColumns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
    },
    {
      title: '任务标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleDateString('zh-CN'),
    },
  ];

  // 最近问题列表列定义
  const issueColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '问题类型',
      dataIndex: 'issue_type',
      key: 'issue_type',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (text: string) => {
        const color = text === 'high' ? 'red' : text === 'medium' ? 'orange' : 'green';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={2}>
            <BarChartOutlined /> 运营数据统计
          </Title>
          <Space>
            <Select
              value={days}
              onChange={setDays}
              style={{ width: 120 }}
            >
              <Option value={7}>最近7天</Option>
              <Option value={30}>最近30天</Option>
              <Option value={90}>最近90天</Option>
            </Select>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        </div>
        
        <Text type="secondary">
          最后更新时间: {new Date(data.last_updated).toLocaleString('zh-CN')}
        </Text>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="总览" key="overview">
          {/* 核心指标大卡片 */}
          <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
            <Col xs={24} sm={12} lg={6}>
              <BigStatCard
                title="总任务数"
                value={data.task_stats.total_tasks}
                icon={<FileTextOutlined />}
                color="#1890ff"
                trend={{ value: 15, isIncrease: true }}
                description="系统累计处理任务数量"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <BigStatCard
                title="成功率"
                value={data.task_stats.success_rate.toFixed(1)}
                icon={<FileTextOutlined />}
                color="#52c41a"
                suffix="%"
                trend={{ value: 2.3, isIncrease: true }}
                description="任务处理成功率"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <BigStatCard
                title="总用户数"
                value={data.user_stats.total_users}
                icon={<UserOutlined />}
                color="#722ed1"
                trend={{ value: 8, isIncrease: true }}
                description="注册用户总数"
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <BigStatCard
                title="AI调用"
                value={data.system_stats.total_ai_calls}
                icon={<DatabaseOutlined />}
                color="#fa8c16"
                trend={{ value: 12, isIncrease: true }}
                description="AI模型调用次数"
              />
            </Col>
          </Row>

          {/* 今日数据 */}
          <Card title="今日数据概览" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="今日任务"
                  value={data.task_stats.tasks_today}
                  icon={<FileTextOutlined />}
                  color="#1890ff"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="今日用户"
                  value={data.user_stats.active_users_today}
                  icon={<UserOutlined />}
                  color="#52c41a"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="新增用户"
                  value={data.user_stats.new_users_today}
                  icon={<UserOutlined />}
                  color="#722ed1"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="AI调用"
                  value={data.system_stats.ai_calls_today}
                  icon={<DatabaseOutlined />}
                  color="#fa8c16"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="发现问题"
                  value={data.issue_stats.total_issues}
                  icon={<ExclamationCircleOutlined />}
                  color="#faad14"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="系统错误"
                  value={data.error_stats.errors_today}
                  icon={<BugOutlined />}
                  color="#f5222d"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="用户反馈"
                  value={Object.values(data.issue_stats.feedback_stats).reduce((a, b) => (a || 0) + (b || 0), 0) - (data.issue_stats.feedback_stats.no_feedback || 0)}
                  icon={<UserOutlined />}
                  color="#722ed1"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="平均满意度"
                  value={data.issue_stats.satisfaction_stats?.average_rating?.toFixed(1) || '0.0'}
                  icon={<UserOutlined />}
                  color="#faad14"
                  suffix="星"
                />
              </Col>
            </Row>
          </Card>

          {/* 系统资源 */}
          <Card title="系统资源概览" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="总文件数"
                  value={data.system_stats.total_files}
                  icon={<DatabaseOutlined />}
                  color="#1890ff"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="文件大小"
                  value={formatBytes(data.system_stats.total_file_size)}
                  icon={<DatabaseOutlined />}
                  color="#52c41a"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="平均处理时间"
                  value={formatProcessingTime(data.task_stats.avg_processing_time)}
                  icon={<FileTextOutlined />}
                  color="#722ed1"
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <StatCard
                  title="管理员"
                  value={data.user_stats.admin_users_count}
                  icon={<UserOutlined />}
                  color="#fa8c16"
                />
              </Col>
            </Row>
          </Card>

          {/* 任务状态进度条 */}
          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            <Col span={24}>
              <Card title="任务状态分布">
                <Row gutter={16}>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={data.task_stats.total_tasks > 0 ? 
                          (data.task_stats.completed_tasks / data.task_stats.total_tasks) * 100 : 0}
                        format={() => `${data.task_stats.completed_tasks}`}
                        strokeColor="#52c41a"
                      />
                      <div style={{ marginTop: 8 }}>已完成</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={data.task_stats.total_tasks > 0 ? 
                          (data.task_stats.processing_tasks / data.task_stats.total_tasks) * 100 : 0}
                        format={() => `${data.task_stats.processing_tasks}`}
                        strokeColor="#1890ff"
                      />
                      <div style={{ marginTop: 8 }}>处理中</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={data.task_stats.total_tasks > 0 ? 
                          (data.task_stats.pending_tasks / data.task_stats.total_tasks) * 100 : 0}
                        format={() => `${data.task_stats.pending_tasks}`}
                        strokeColor="#faad14"
                      />
                      <div style={{ marginTop: 8 }}>待处理</div>
                    </div>
                  </Col>
                  <Col span={6}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={data.task_stats.total_tasks > 0 ? 
                          (data.task_stats.failed_tasks / data.task_stats.total_tasks) * 100 : 0}
                        format={() => `${data.task_stats.failed_tasks}`}
                        strokeColor="#f5222d"
                      />
                      <div style={{ marginTop: 8 }}>失败</div>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="用户分析" key="users">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="用户注册趋势">
                <TrendChart
                  data={data.user_stats.user_registration_trend}
                  title="最近7天新用户注册"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="用户活跃趋势">
                <TrendChart
                  data={data.user_stats.user_activity_trend}
                  title="最近7天用户活跃"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="任务分析" key="tasks">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="任务创建趋势">
                <TrendChart
                  data={data.task_stats.task_creation_trend}
                  title="最近7天任务创建"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="任务完成趋势">
                <TrendChart
                  data={data.task_stats.task_completion_trend}
                  title="最近7天任务完成"
                />
              </Card>
            </Col>
            <Col span={24}>
              <Card title="任务状态分布">
                <PieChart
                  data={data.task_stats.task_status_distribution}
                  title="任务状态分布"
                  nameKey="status"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="系统资源" key="system">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="文件类型分布">
                <PieChart
                  data={data.system_stats.file_type_distribution}
                  title="文件类型分布"
                  nameKey="file_type"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="AI模型使用情况">
                <PieChart
                  data={data.system_stats.ai_model_usage}
                  title="AI模型使用分布"
                  nameKey="model_name"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="问题与错误" key="issues">
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="问题严重程度分布">
                <PieChart
                  data={data.issue_stats.issues_by_severity}
                  title="问题严重程度"
                  nameKey="severity"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="问题类型分布">
                <PieChart
                  data={data.issue_stats.issues_by_type}
                  title="问题类型"
                  nameKey="type"
                />
              </Card>
            </Col>
            {/* 用户反馈统计 */}
            <Col span={12}>
              <Card title="用户反馈统计">
                <div style={{ marginBottom: 16 }}>
                  <Text strong>反馈情况</Text>
                  <div style={{ marginTop: 8 }}>
                    {Object.entries(data.issue_stats.feedback_stats).map(([key, value]) => (
                      <div key={key} style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: '#666' }}>
                          {key === 'accept' ? '✅ 已接受' : 
                           key === 'reject' ? '❌ 已拒绝' : 
                           key === 'no_feedback' ? '⏳ 未反馈' : key}:
                        </span>
                        <Tag color={key === 'accept' ? 'green' : key === 'reject' ? 'red' : 'default'}>
                          {value}
                        </Tag>
                      </div>
                    ))}
                  </div>
                  <div style={{ marginTop: 16 }}>
                    <Progress 
                      percent={data.issue_stats.total_issues > 0 
                        ? ((data.issue_stats.feedback_stats.accept || 0) / data.issue_stats.total_issues * 100)
                        : 0
                      }
                      strokeColor="#52c41a"
                      format={(percent) => `接受率 ${percent?.toFixed(1)}%`}
                    />
                  </div>
                </div>
              </Card>
            </Col>
            {/* 用户满意度统计 */}
            <Col span={12}>
              <Card title="用户满意度统计">
                <div style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic
                        title="平均评分"
                        value={data.issue_stats.satisfaction_stats?.average_rating || 0}
                        precision={1}
                        suffix="星"
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="评分总数"
                        value={data.issue_stats.satisfaction_stats?.total_ratings || 0}
                        suffix="个"
                      />
                    </Col>
                  </Row>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>高满意度 (4星+):</Text>
                    <Tag color="green">
                      {data.issue_stats.satisfaction_stats?.high_satisfaction_rate?.toFixed(1) || 0}%
                    </Tag>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text>低满意度 (2星-):</Text>
                    <Tag color="red">
                      {data.issue_stats.satisfaction_stats?.low_satisfaction_rate?.toFixed(1) || 0}%
                    </Tag>
                  </div>
                </div>
                {/* 评分分布图 */}
                {data.issue_stats.satisfaction_stats?.rating_distribution && (
                  <div>
                    <Text strong style={{ marginBottom: 8, display: 'block' }}>评分分布</Text>
                    {data.issue_stats.satisfaction_stats.rating_distribution.map((item) => (
                      <div key={item.rating} style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        marginBottom: 4 
                      }}>
                        <span style={{ width: 60, fontSize: 12 }}>
                          {item.rating}星:
                        </span>
                        <Progress 
                          percent={data.issue_stats.satisfaction_stats.total_ratings > 0 
                            ? (item.count / data.issue_stats.satisfaction_stats.total_ratings * 100)
                            : 0
                          }
                          size="small"
                          strokeColor="#faad14"
                          format={() => item.count}
                          style={{ flex: 1, marginLeft: 8 }}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
            <Col span={24}>
              <Card title="最近发现的问题">
                <Table
                  columns={issueColumns}
                  dataSource={data.issue_stats.recent_issues}
                  pagination={{ pageSize: 5 }}
                  size="small"
                />
              </Card>
            </Col>
            <Col span={24}>
              <Card title="最近的系统错误">
                <Table
                  columns={errorColumns}
                  dataSource={data.error_stats.recent_errors}
                  pagination={{ pageSize: 5 }}
                  size="small"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Analytics;