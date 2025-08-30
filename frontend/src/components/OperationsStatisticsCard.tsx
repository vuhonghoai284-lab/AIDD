import React from 'react';
import { Card, Row, Col, Statistic, Tag, Typography } from 'antd';
import { 
  CheckCircleOutlined, 
  ClockCircleOutlined,
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
  TokenConsumption,
  TrendDataPoint
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
      style={{
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        border: 'none',
        transition: 'all 0.3s ease'
      }}
      className="statistics-card"
    >
      {/* 今日数据突出显示在顶部 */}
      <div style={{ 
        marginBottom: 20,
        backgroundColor: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
        borderRadius: '12px',
        padding: '20px 16px',
        border: '2px solid #bae7ff',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #1890ff 0%, #40a9ff 100%)'
        }}></div>
        
        <Title level={4} style={{ 
          margin: 0, 
          marginBottom: 16, 
          fontSize: '18px',
          fontWeight: 'bold',
          color: '#1890ff',
          textAlign: 'center',
          letterSpacing: '0.5px'
        }}>
          📊 今日任务数据
        </Title>
        
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '28px', 
                fontWeight: 900, 
                color: '#1890ff',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(24, 144, 255, 0.2)'
              }}>
                {data.today_total}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                新增任务
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '28px', 
                fontWeight: 900, 
                color: '#52c41a',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(82, 196, 26, 0.2)'
              }}>
                {data.today_completed}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                完成任务
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '28px', 
                fontWeight: 900, 
                color: '#ff4d4f',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(255, 77, 79, 0.2)'
              }}>
                {data.today_failed}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                失败任务
              </div>
            </div>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]} style={{ height: '200px' }}>
        <Col xs={24} sm={12}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'center',
            height: '100%',
            padding: '8px 0'
          }}>
            <div style={{ 
              textAlign: 'center', 
              marginBottom: 20,
              backgroundColor: '#f8faff',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid #e8f4fd'
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>总任务数</span>}
                value={data.total}
                prefix={<ClockCircleOutlined style={{ fontSize: '16px' }} />}
                valueStyle={{ 
                  fontSize: '26px', 
                  color: '#1890ff',
                  fontWeight: 'bold',
                  lineHeight: 1.2
                }}
              />
            </div>
            <div style={{ 
              textAlign: 'center',
              backgroundColor: data.success_rate >= 80 ? '#f6ffed' : '#fff2f0',
              padding: '16px',
              borderRadius: '8px',
              border: `1px solid ${data.success_rate >= 80 ? '#d9f7be' : '#ffccc7'}`
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>成功率</span>}
                value={data.success_rate}
                suffix="%" 
                precision={1}
                valueStyle={{ 
                  fontSize: '22px',
                  fontWeight: 'bold',
                  lineHeight: 1.2,
                  color: data.success_rate >= 80 ? '#52c41a' : '#ff4d4f' 
                }}
              />
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <div style={{ height: '160px' }}>
            <ReactECharts 
              option={pieOption} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
            />
          </div>
        </Col>
      </Row>
    </Card>
  );
};

interface UserCardProps {
  data: UserStatistics;
  trends?: TrendDataPoint[];
  loading?: boolean;
}

export const UserStatisticsCard: React.FC<UserCardProps> = ({ data, trends = [], loading = false }) => {
  
  // 折线图配置
  const lineOption: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0];
        const point = trends.find(t => t.date === data.name);
        return `
          <div>
            <div>${data.name}</div>
            <div>新增用户: ${point?.new_users || 0}人</div>
            <div>活跃用户: ${point?.active_users || 0}人</div>
            <div>总计: ${data.value}人</div>
          </div>
        `;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: trends.map(t => {
        const date = new Date(t.date);
        return `${date.getMonth() + 1}/${date.getDate()}`;
      }),
      axisLabel: {
        fontSize: 10,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '新增用户',
        type: 'line',
        data: trends.map(t => t.new_users || 0),
        smooth: true,
        itemStyle: { color: '#52c41a' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.1)' }
            ]
          }
        }
      },
      {
        name: '活跃用户',
        type: 'line',
        data: trends.map(t => t.active_users || 0),
        smooth: true,
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.1)' }
            ]
          }
        }
      }
    ],
    legend: {
      bottom: '5%',
      textStyle: { fontSize: 12 }
    }
  };


  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <UserOutlined style={{ color: '#1890ff' }} />
          <span>用户统计</span>
        </div>
      }
      loading={loading}
      size="small"
      style={{
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        border: 'none',
        transition: 'all 0.3s ease'
      }}
      className="statistics-card"
    >
      {/* 今日数据突出显示在顶部 */}
      <div style={{ 
        marginBottom: 20,
        backgroundColor: 'linear-gradient(135deg, #f6ffed 0%, #e6fffb 100%)',
        borderRadius: '12px',
        padding: '20px 16px',
        border: '2px solid #b7eb8f',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #52c41a 0%, #73d13d 100%)'
        }}></div>
        
        <Title level={4} style={{ 
          margin: 0, 
          marginBottom: 16, 
          fontSize: '18px',
          fontWeight: 'bold',
          color: '#52c41a',
          textAlign: 'center',
          letterSpacing: '0.5px'
        }}>
          👥 今日用户数据
        </Title>
        
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '32px', 
                fontWeight: 900, 
                color: '#52c41a',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(82, 196, 26, 0.2)'
              }}>
                {data.today_new_registrations}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                新注册用户
              </div>
            </div>
          </Col>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '32px', 
                fontWeight: 900, 
                color: '#1890ff',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(24, 144, 255, 0.2)'
              }}>
                {data.today_active}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                活跃用户
              </div>
            </div>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]} style={{ height: '200px' }}>
        <Col xs={24} sm={12}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'space-around',
            height: '100%',
            padding: '8px 0'
          }}>
            <div style={{ 
              textAlign: 'center',
              backgroundColor: '#f8faff',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid #e8f4fd',
              marginBottom: '12px'
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>总用户数</span>}
                value={data.total_users}
                prefix={<UserOutlined style={{ fontSize: '16px', color: '#1890ff' }} />}
                valueStyle={{ 
                  fontSize: '24px', 
                  color: '#1890ff',
                  fontWeight: 'bold',
                  lineHeight: 1.2
                }}
              />
            </div>
            
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              gap: '12px'
            }}>
              <div style={{
                flex: 1,
                textAlign: 'center',
                backgroundColor: '#f6ffed',
                padding: '10px 8px',
                borderRadius: '6px',
                border: '1px solid #d9f7be'
              }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>活跃</div>
                <div style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold', 
                  color: '#52c41a',
                  lineHeight: 1.2 
                }}>
                  {data.active_users}
                </div>
              </div>
              
              <div style={{
                flex: 1,
                textAlign: 'center',
                backgroundColor: '#fff7e6',
                padding: '10px 8px',
                borderRadius: '6px',
                border: '1px solid #ffd591'
              }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>在线</div>
                <div style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold', 
                  color: '#fa8c16',
                  lineHeight: 1.2 
                }}>
                  {data.current_online}
                </div>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <div style={{ height: '160px' }}>
            <ReactECharts 
              option={lineOption} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
            />
          </div>
        </Col>
      </Row>
    </Card>
  );
};

interface IssueCardProps {
  data: IssueStatistics;
  loading?: boolean;
}

export const IssueStatisticsCard: React.FC<IssueCardProps> = ({ data, loading = false }) => {
  const barOption: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      bottom: '5%',
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['致命', '严重', '中等', '轻微']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '问题数量',
        type: 'bar',
        data: [
          { 
            value: data.critical_issues,
            itemStyle: { color: '#ff4d4f' }
          },
          { 
            value: data.high_issues,
            itemStyle: { color: '#fa8c16' }
          },
          { 
            value: data.medium_issues,
            itemStyle: { color: '#faad14' }
          },
          { 
            value: data.low_issues,
            itemStyle: { color: '#52c41a' }
          }
        ],
        barWidth: '60%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
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
      style={{
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        border: 'none',
        transition: 'all 0.3s ease'
      }}
      className="statistics-card"
    >
      {/* 今日数据突出显示在顶部 */}
      <div style={{ 
        marginBottom: 20,
        backgroundColor: 'linear-gradient(135deg, #fff7e6 0%, #fff2e8 100%)',
        borderRadius: '12px',
        padding: '20px 16px',
        border: '2px solid #ffd591',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #fa8c16 0%, #ffa940 100%)'
        }}></div>
        
        <Title level={4} style={{ 
          margin: 0, 
          marginBottom: 16, 
          fontSize: '18px',
          fontWeight: 'bold',
          color: '#fa8c16',
          textAlign: 'center',
          letterSpacing: '0.5px'
        }}>
          🐛 今日问题数据
        </Title>
        
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '30px', 
                fontWeight: 900, 
                color: '#fa8c16',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(250, 140, 22, 0.2)'
              }}>
                {data.today_new}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                新增问题
              </div>
            </div>
          </Col>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: '30px', 
                fontWeight: 900, 
                color: '#52c41a',
                marginBottom: '4px',
                textShadow: '0 2px 4px rgba(82, 196, 26, 0.2)'
              }}>
                {data.today_accepted}
              </div>
              <div style={{ 
                fontSize: '14px', 
                color: '#666',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                已接受问题
              </div>
            </div>
          </Col>
        </Row>
      </div>

      <Row gutter={[16, 16]} style={{ height: '200px' }}>
        <Col xs={24} sm={12}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'space-between',
            height: '100%',
            padding: '8px 0'
          }}>
            <div style={{ 
              textAlign: 'center',
              backgroundColor: '#fff7e6',
              padding: '14px',
              borderRadius: '8px',
              border: '1px solid #ffd591',
              marginBottom: '12px'
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>总问题数</span>}
                value={data.total_issues}
                prefix={<BugOutlined style={{ fontSize: '16px', color: '#fa8c16' }} />}
                valueStyle={{ 
                  fontSize: '22px', 
                  color: '#fa8c16',
                  fontWeight: 'bold',
                  lineHeight: 1.2
                }}
              />
            </div>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr 1fr',
              gap: '8px'
            }}>
              <div style={{
                textAlign: 'center',
                backgroundColor: '#fff7e6',
                padding: '8px 6px',
                borderRadius: '6px',
                border: '1px solid #ffd591'
              }}>
                <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>待处理</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: 'bold', 
                  color: '#faad14',
                  lineHeight: 1.2 
                }}>
                  {data.pending_issues}
                </div>
              </div>
              
              <div style={{
                textAlign: 'center',
                backgroundColor: '#f6ffed',
                padding: '8px 6px',
                borderRadius: '6px',
                border: '1px solid #d9f7be'
              }}>
                <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>已接受</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: 'bold', 
                  color: '#52c41a',
                  lineHeight: 1.2 
                }}>
                  {data.accepted_issues}
                </div>
              </div>
              
              <div style={{
                textAlign: 'center',
                backgroundColor: '#fff2f0',
                padding: '8px 6px',
                borderRadius: '6px',
                border: '1px solid #ffccc7'
              }}>
                <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>已拒绝</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: 'bold', 
                  color: '#ff4d4f',
                  lineHeight: 1.2 
                }}>
                  {data.rejected_issues}
                </div>
              </div>
              
              <div style={{
                textAlign: 'center',
                backgroundColor: '#ff4d4f20',
                padding: '8px 6px',
                borderRadius: '6px',
                border: '1px solid #ff4d4f40'
              }}>
                <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>致命</div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: 'bold', 
                  color: '#ff4d4f',
                  lineHeight: 1.2 
                }}>
                  {data.critical_issues}
                </div>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <div style={{ height: '160px' }}>
            <ReactECharts 
              option={barOption} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
            />
          </div>
        </Col>
      </Row>
    </Card>
  );
};

interface FeedbackCardProps {
  data: FeedbackStatistics;
  loading?: boolean;
}

export const FeedbackStatisticsCard: React.FC<FeedbackCardProps> = ({ data, loading = false }) => {
  const radarOption: EChartsOption = {
    tooltip: {
      trigger: 'item'
    },
    radar: {
      center: ['50%', '50%'],
      radius: '70%',
      indicator: Object.keys(data.score_distribution).length > 0 
        ? Object.entries(data.score_distribution).map(([score, count]) => ({
            name: `${score}分`,
            max: Math.max(...Object.values(data.score_distribution)) || 10
          }))
        : [
            { name: '5分', max: 10 },
            { name: '4分', max: 10 },
            { name: '3分', max: 10 },
            { name: '2分', max: 10 },
            { name: '1分', max: 10 }
          ],
      axisName: {
        color: '#666',
        fontSize: 12
      }
    },
    series: [
      {
        name: '评分分布',
        type: 'radar',
        data: [
          {
            value: Object.keys(data.score_distribution).length > 0
              ? Object.values(data.score_distribution)
              : [0, 0, 0, 0, 0],
            name: '反馈评分',
            itemStyle: {
              color: '#722ed1'
            },
            areaStyle: {
              color: 'rgba(114, 46, 209, 0.2)'
            }
          }
        ]
      }
    ]
  };

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CommentOutlined style={{ color: '#722ed1' }} />
          <span>用户反馈</span>
        </div>
      }
      loading={loading}
      size="small"
      style={{
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        border: 'none',
        transition: 'all 0.3s ease'
      }}
      className="statistics-card"
    >
      <Row gutter={[16, 16]} style={{ height: '240px' }}>
        <Col xs={24} sm={12}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'space-between',
            height: '100%',
            padding: '8px 0'
          }}>
            <div style={{ 
              textAlign: 'center',
              backgroundColor: '#f9f0ff',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid #efdbff',
              marginBottom: '12px'
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>平均评分</span>}
                value={data.average_score}
                precision={1}
                suffix="分"
                prefix={<CommentOutlined style={{ fontSize: '16px', color: '#722ed1' }} />}
                valueStyle={{ 
                  fontSize: '26px',
                  fontWeight: 'bold',
                  lineHeight: 1.2,
                  color: data.average_score >= 4 ? '#52c41a' : 
                         data.average_score >= 3 ? '#faad14' : '#ff4d4f' 
                }}
              />
            </div>
            
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              gap: '12px'
            }}>
              <div style={{
                flex: 1,
                textAlign: 'center',
                backgroundColor: '#f9f0ff',
                padding: '12px 8px',
                borderRadius: '6px',
                border: '1px solid #efdbff'
              }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>总反馈</div>
                <div style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold', 
                  color: '#722ed1',
                  lineHeight: 1.2 
                }}>
                  {data.total_feedback}
                </div>
              </div>
              
              <div style={{
                flex: 1,
                textAlign: 'center',
                backgroundColor: '#f6ffed',
                padding: '12px 8px',
                borderRadius: '6px',
                border: '1px solid #d9f7be'
              }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>有效</div>
                <div style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold', 
                  color: '#52c41a',
                  lineHeight: 1.2 
                }}>
                  {data.valid_feedback}
                </div>
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <div style={{ height: '200px' }}>
            <ReactECharts 
              option={radarOption} 
              style={{ height: '100%', width: '100%' }}
              opts={{ renderer: 'svg' }}
            />
          </div>
        </Col>
      </Row>

      <div style={{ 
        marginTop: 16, 
        borderTop: '2px solid #f0f0f0', 
        backgroundColor: '#fafafa',
        borderRadius: '0 0 6px 6px',
        margin: '16px -24px -16px -24px',
        padding: '16px 24px'
      }}>
        <Title level={5} style={{ 
          margin: 0, 
          marginBottom: 12, 
          fontSize: '14px',
          color: '#595959',
          textAlign: 'center'
        }}>
          💬 今日数据
        </Title>
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <Statistic 
                title={<span style={{ fontSize: '12px', color: '#8c8c8c' }}>新反馈</span>}
                value={data.today_feedback} 
                valueStyle={{ 
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#722ed1'
                }}
              />
            </div>
          </Col>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <Statistic 
                title={<span style={{ fontSize: '12px', color: '#8c8c8c' }}>今日评分</span>}
                value={data.today_average_score}
                precision={1}
                suffix="分"
                valueStyle={{ 
                  fontSize: '16px',
                  fontWeight: 600,
                  color: data.today_average_score >= 4 ? '#52c41a' : 
                         data.today_average_score >= 3 ? '#faad14' : '#ff4d4f' 
                }}
              />
            </div>
          </Col>
        </Row>
      </div>
    </Card>
  );
};

interface TokenCardProps {
  data: TokenConsumption;
  loading?: boolean;
}

export const TokenStatisticsCard: React.FC<TokenCardProps> = ({ data, loading = false }) => {
  const modelData = Object.keys(data.by_model).length > 0 
    ? Object.entries(data.by_model).map(([model, tokens]) => ({
        value: tokens,
        name: model,
        itemStyle: {
          color: model.includes('gpt') ? '#52c41a' : 
                 model.includes('claude') ? '#1890ff' : '#fa8c16'
        }
      }))
    : [{ value: 1, name: '暂无数据', itemStyle: { color: '#d9d9d9' } }];

  const pieOption: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} tokens ({d}%)'
    },
    legend: {
      bottom: '5%',
      left: 'center',
      textStyle: { fontSize: 10 }
    },
    series: [
      {
        type: 'pie',
        radius: ['30%', '60%'],
        center: ['50%', '45%'],
        data: modelData,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold'
          }
        }
      }
    ]
  };

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <DollarOutlined style={{ color: '#13c2c2' }} />
          <span>Token消耗</span>
        </div>
      }
      loading={loading}
      size="small"
      style={{
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
        border: 'none',
        transition: 'all 0.3s ease'
      }}
      className="statistics-card"
    >
      <Row gutter={[16, 16]} style={{ height: '240px' }}>
        <Col xs={24} sm={12}>
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'space-between',
            height: '100%',
            padding: '8px 0'
          }}>
            <div style={{ 
              textAlign: 'center',
              backgroundColor: '#e6fffb',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid #87e8de',
              marginBottom: '12px'
            }}>
              <Statistic 
                title={<span style={{ fontSize: '13px', fontWeight: 500 }}>预估成本</span>}
                value={data.estimated_cost}
                precision={4}
                prefix="$"
                valueStyle={{ 
                  fontSize: '26px', 
                  color: '#fa8c16',
                  fontWeight: 'bold',
                  lineHeight: 1.2
                }}
              />
            </div>
            
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column',
              gap: '8px'
            }}>
              <div style={{
                textAlign: 'center',
                backgroundColor: '#e6fffb',
                padding: '10px 12px',
                borderRadius: '6px',
                border: '1px solid #87e8de'
              }}>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '2px' }}>总Token数</div>
                <div style={{ 
                  fontSize: '16px', 
                  fontWeight: 'bold', 
                  color: '#13c2c2',
                  lineHeight: 1.2 
                }}>
                  {(data.total_tokens / 1000).toFixed(1)}K
                </div>
              </div>
              
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: '8px'
              }}>
                <div style={{
                  flex: 1,
                  textAlign: 'center',
                  backgroundColor: '#f6ffed',
                  padding: '8px 6px',
                  borderRadius: '6px',
                  border: '1px solid #d9f7be'
                }}>
                  <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>输入</div>
                  <div style={{ 
                    fontSize: '14px', 
                    fontWeight: 'bold', 
                    color: '#52c41a',
                    lineHeight: 1.2 
                  }}>
                    {(data.input_tokens / 1000).toFixed(1)}K
                  </div>
                </div>
                
                <div style={{
                  flex: 1,
                  textAlign: 'center',
                  backgroundColor: '#fff7e6',
                  padding: '8px 6px',
                  borderRadius: '6px',
                  border: '1px solid #ffd591'
                }}>
                  <div style={{ fontSize: '11px', color: '#8c8c8c', marginBottom: '2px' }}>输出</div>
                  <div style={{ 
                    fontSize: '14px', 
                    fontWeight: 'bold', 
                    color: '#fa8c16',
                    lineHeight: 1.2 
                  }}>
                    {(data.output_tokens / 1000).toFixed(1)}K
                  </div>
                </div>
              </div>
            </div>
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

      <div style={{ 
        marginTop: 16, 
        borderTop: '2px solid #f0f0f0', 
        backgroundColor: '#fafafa',
        borderRadius: '0 0 6px 6px',
        margin: '16px -24px -16px -24px',
        padding: '16px 24px'
      }}>
        <Title level={5} style={{ 
          margin: 0, 
          marginBottom: 12, 
          fontSize: '14px',
          color: '#595959',
          textAlign: 'center'
        }}>
          💰 今日数据
        </Title>
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <Statistic 
                title={<span style={{ fontSize: '12px', color: '#8c8c8c' }}>今日Token</span>}
                value={data.today_tokens}
                formatter={(value) => `${(Number(value) / 1000).toFixed(1)}K`}
                valueStyle={{ 
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#13c2c2'
                }}
              />
            </div>
          </Col>
          <Col span={12}>
            <div style={{ textAlign: 'center' }}>
              <Statistic 
                title={<span style={{ fontSize: '12px', color: '#8c8c8c' }}>今日成本</span>}
                value={data.today_cost}
                precision={4}
                prefix="$"
                valueStyle={{ 
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#fa8c16'
                }}
              />
            </div>
          </Col>
        </Row>
      </div>
    </Card>
  );
};