import React from 'react';
import { Card, Row, Col, Statistic, Progress, Tag, Typography } from 'antd';
import { 
  CheckCircleOutlined, 
  ClockCircleOutlined, 
  ExclamationCircleOutlined,
  UserOutlined,
  CommentOutlined,
  BugOutlined,
  DollarOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { 
  TaskStatistics, 
  UserStatistics, 
  IssueStatistics, 
  FeedbackStatistics, 
  TokenConsumption 
} from '../types/operations';

const { Text, Title } = Typography;

interface TaskCardProps {
  data: TaskStatistics;
  loading?: boolean;
}

export const TaskStatisticsCard: React.FC<TaskCardProps> = ({ data, loading = false }) => {
  const pieOption: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: '5%',
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: [
          { 
            value: data.completed, 
            name: '已完成',
            itemStyle: { color: '#52c41a' }
          },
          { 
            value: data.running, 
            name: '运行中',
            itemStyle: { color: '#1890ff' }
          },
          { 
            value: data.failed, 
            name: '失败',
            itemStyle: { color: '#ff4d4f' }
          }
        ]
      }
    ]
  };

  return (
  <Card 
    title={
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <CheckCircleOutlined style={{ color: '#52c41a' }} />
        <span>任务统计</span>
      </div>
    }
    loading={loading}
    size="small"
  >
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12}>
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <Statistic 
            title="总任务数" 
            value={data.total}
            prefix={<ClockCircleOutlined />}
            valueStyle={{ fontSize: '24px', color: '#1890ff' }}
          />
        </div>
        <div style={{ textAlign: 'center' }}>
          <Statistic 
            title="成功率" 
            value={data.success_rate}
            suffix="%" 
            precision={1}
            valueStyle={{ 
              fontSize: '20px',
              color: data.success_rate >= 80 ? '#52c41a' : '#ff4d4f' 
            }}
          />
        </div>
      </Col>
      <Col xs={24} sm={12}>
        <div style={{ height: '200px' }}>
          <ReactECharts 
            option={pieOption} 
            style={{ height: '100%', width: '100%' }}
            opts={{ renderer: 'svg' }}
          />
        </div>
      </Col>
    </Row>

    <div style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
      <Title level={5} style={{ margin: 0, marginBottom: 8 }}>今日数据</Title>
      <Row gutter={16}>
        <Col span={8}>
          <Statistic title="新增" value={data.today_total} size="small" />
        </Col>
        <Col span={8}>
          <Statistic 
            title="完成" 
            value={data.today_completed} 
            size="small"
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
        <Col span={8}>
          <Statistic 
            title="失败" 
            value={data.today_failed} 
            size="small"
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Col>
      </Row>
    </div>
  </Card>
  );
};

interface UserCardProps {
  data: UserStatistics;
  loading?: boolean;
}

export const UserStatisticsCard: React.FC<UserCardProps> = ({ data, loading = false }) => (
  <Card 
    title={
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <UserOutlined style={{ color: '#1890ff' }} />
        <span>用户统计</span>
      </div>
    }
    loading={loading}
    size="small"
  >
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={8}>
        <Statistic title="总用户数" value={data.total_users} />
      </Col>
      <Col xs={12} sm={8}>
        <Statistic 
          title="活跃用户" 
          value={data.active_users}
          valueStyle={{ color: '#52c41a' }}
        />
      </Col>
      <Col xs={12} sm={8}>
        <div style={{ textAlign: 'center' }}>
          <Tag color="green">在线 {data.current_online}</Tag>
        </div>
      </Col>
    </Row>

    <div style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
      <Title level={5} style={{ margin: 0, marginBottom: 8 }}>今日数据</Title>
      <Row gutter={16}>
        <Col span={12}>
          <Statistic title="新注册" value={data.today_new_registrations} size="small" />
        </Col>
        <Col span={12}>
          <Statistic 
            title="活跃" 
            value={data.today_active} 
            size="small"
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
      </Row>
    </div>
  </Card>
);

interface IssueCardProps {
  data: IssueStatistics;
  loading?: boolean;
}

export const IssueStatisticsCard: React.FC<IssueCardProps> = ({ data, loading = false }) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ff4d4f';
      case 'high': return '#fa8c16';
      case 'medium': return '#faad14';
      case 'low': return '#52c41a';
      default: return '#d9d9d9';
    }
  };

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BugOutlined style={{ color: '#fa8c16' }} />
          <span>问题统计</span>
        </div>
      }
      loading={loading}
      size="small"
    >
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Statistic title="总问题数" value={data.total_issues} />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic 
            title="已接受" 
            value={data.accepted_issues}
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic 
            title="已拒绝" 
            value={data.rejected_issues}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic 
            title="待处理" 
            value={data.pending_issues}
            valueStyle={{ color: '#faad14' }}
          />
        </Col>
      </Row>

      <div style={{ marginTop: 16 }}>
        <Title level={5} style={{ margin: 0, marginBottom: 8 }}>严重程度分布</Title>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="red">致命 {data.critical_issues}</Tag>
          <Tag color="orange">严重 {data.high_issues}</Tag>
          <Tag color="gold">中等 {data.medium_issues}</Tag>
          <Tag color="green">轻微 {data.low_issues}</Tag>
        </div>
      </div>

      <div style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
        <Title level={5} style={{ margin: 0, marginBottom: 8 }}>今日数据</Title>
        <Row gutter={16}>
          <Col span={12}>
            <Statistic title="新增问题" value={data.today_new} size="small" />
          </Col>
          <Col span={12}>
            <Statistic 
              title="已接受" 
              value={data.today_accepted} 
              size="small"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
        </Row>
      </div>
    </Card>
  );
};

interface FeedbackCardProps {
  data: FeedbackStatistics;
  loading?: boolean;
}

export const FeedbackStatisticsCard: React.FC<FeedbackCardProps> = ({ data, loading = false }) => (
  <Card 
    title={
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <CommentOutlined style={{ color: '#722ed1' }} />
        <span>用户反馈</span>
      </div>
    }
    loading={loading}
    size="small"
  >
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={8}>
        <Statistic title="总反馈数" value={data.total_feedback} />
      </Col>
      <Col xs={12} sm={8}>
        <Statistic title="有效反馈" value={data.valid_feedback} />
      </Col>
      <Col xs={12} sm={8}>
        <Statistic 
          title="平均评分" 
          value={data.average_score}
          precision={1}
          suffix="分"
          valueStyle={{ 
            color: data.average_score >= 4 ? '#52c41a' : 
                   data.average_score >= 3 ? '#faad14' : '#ff4d4f' 
          }}
        />
      </Col>
    </Row>

    {Object.keys(data.score_distribution).length > 0 && (
      <div style={{ marginTop: 16 }}>
        <Title level={5} style={{ margin: 0, marginBottom: 8 }}>评分分布</Title>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {Object.entries(data.score_distribution).map(([score, count]) => (
            <Tag key={score} color="blue">{score}分: {count}</Tag>
          ))}
        </div>
      </div>
    )}

    <div style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
      <Title level={5} style={{ margin: 0, marginBottom: 8 }}>今日数据</Title>
      <Row gutter={16}>
        <Col span={12}>
          <Statistic title="新反馈" value={data.today_feedback} size="small" />
        </Col>
        <Col span={12}>
          <Statistic 
            title="今日评分" 
            value={data.today_average_score}
            precision={1}
            suffix="分"
            size="small"
            valueStyle={{ 
              color: data.today_average_score >= 4 ? '#52c41a' : 
                     data.today_average_score >= 3 ? '#faad14' : '#ff4d4f' 
            }}
          />
        </Col>
      </Row>
    </div>
  </Card>
);

interface TokenCardProps {
  data: TokenConsumption;
  loading?: boolean;
}

export const TokenStatisticsCard: React.FC<TokenCardProps> = ({ data, loading = false }) => (
  <Card 
    title={
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <DollarOutlined style={{ color: '#13c2c2' }} />
        <span>Token消耗</span>
      </div>
    }
    loading={loading}
    size="small"
  >
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={8}>
        <Statistic 
          title="总Token数" 
          value={data.total_tokens}
          formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
        />
      </Col>
      <Col xs={12} sm={8}>
        <Statistic 
          title="预估成本" 
          value={data.estimated_cost}
          precision={4}
          prefix="$"
          valueStyle={{ color: '#fa8c16' }}
        />
      </Col>
      <Col xs={12} sm={8}>
        <div>
          <Text type="secondary">输入/输出</Text>
          <div>
            <Text>{(data.input_tokens / 1000).toFixed(1)}K / {(data.output_tokens / 1000).toFixed(1)}K</Text>
          </div>
        </div>
      </Col>
    </Row>

    {Object.keys(data.by_model).length > 0 && (
      <div style={{ marginTop: 16 }}>
        <Title level={5} style={{ margin: 0, marginBottom: 8 }}>按模型分布</Title>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {Object.entries(data.by_model).map(([model, tokens]) => (
            <Tag key={model} color="cyan">
              {model}: {(tokens / 1000).toFixed(1)}K
            </Tag>
          ))}
        </div>
      </div>
    )}

    <div style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
      <Title level={5} style={{ margin: 0, marginBottom: 8 }}>今日数据</Title>
      <Row gutter={16}>
        <Col span={12}>
          <Statistic 
            title="今日Token" 
            value={data.today_tokens}
            formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
            size="small" 
          />
        </Col>
        <Col span={12}>
          <Statistic 
            title="今日成本" 
            value={data.today_cost}
            precision={4}
            prefix="$"
            size="small"
            valueStyle={{ color: '#fa8c16' }}
          />
        </Col>
      </Row>
    </div>
  </Card>
);