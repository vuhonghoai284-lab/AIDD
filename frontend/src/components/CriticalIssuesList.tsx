import React from 'react';
import { Card, List, Tag, Typography, Tooltip, Space, Button } from 'antd';
import { 
  ExclamationCircleOutlined, 
  BugOutlined,
  EyeOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import type { CriticalIssueItem } from '../types/operations';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text, Paragraph } = Typography;

interface CriticalIssuesListProps {
  issues: CriticalIssueItem[];
  loading?: boolean;
  onViewIssue?: (issueId: number, taskId: number) => void;
  maxHeight?: number;
}

const CriticalIssuesList: React.FC<CriticalIssuesListProps> = ({
  issues,
  loading = false,
  onViewIssue,
  maxHeight = 400,
}) => {
  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'critical':
        return { color: 'red', icon: <ExclamationCircleOutlined />, label: '致命' };
      case 'high':
        return { color: 'orange', icon: <ExclamationCircleOutlined />, label: '严重' };
      case 'medium':
        return { color: 'gold', icon: <BugOutlined />, label: '中等' };
      case 'low':
        return { color: 'green', icon: <BugOutlined />, label: '轻微' };
      default:
        return { color: 'default', icon: <BugOutlined />, label: '未知' };
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'accept':
      case 'accepted':
        return { color: 'success', label: '已接受' };
      case 'reject':
      case 'rejected':
        return { color: 'error', label: '已拒绝' };
      case 'pending':
        return { color: 'processing', label: '待处理' };
      default:
        return { color: 'default', label: status };
    }
  };

  const handleViewIssue = (issue: CriticalIssueItem) => {
    onViewIssue?.(issue.id, issue.task_id);
  };

  const renderIssueItem = (issue: CriticalIssueItem) => {
    const severityConfig = getSeverityConfig(issue.severity);
    const statusConfig = getStatusConfig(issue.status);
    const createdTime = dayjs(issue.created_at);

    return (
      <List.Item
        key={issue.id}
        actions={[
          <Button
            key="view"
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewIssue(issue)}
          >
            查看
          </Button>
        ]}
      >
        <List.Item.Meta
          title={
            <Space>
              <Tag 
                color={severityConfig.color} 
                icon={severityConfig.icon}
              >
                {severityConfig.label}
              </Tag>
              <Tooltip title={issue.title}>
                <Text strong style={{ maxWidth: 200 }} ellipsis>
                  {issue.title}
                </Text>
              </Tooltip>
              <Tag color={statusConfig.color}>
                {statusConfig.label}
              </Tag>
            </Space>
          }
          description={
            <div>
              <Paragraph
                ellipsis={{ rows: 2, tooltip: issue.description }}
                style={{ marginBottom: 8, color: '#666' }}
              >
                {issue.description}
              </Paragraph>
              <Space size="middle">
                <Text type="secondary">
                  <BugOutlined /> {issue.issue_type}
                </Text>
                <Tooltip title={issue.task_title}>
                  <Text type="secondary" ellipsis style={{ maxWidth: 150 }}>
                    任务: {issue.task_title}
                  </Text>
                </Tooltip>
                <Text type="secondary">
                  <ClockCircleOutlined /> {createdTime.fromNow()}
                </Text>
              </Space>
            </div>
          }
        />
      </List.Item>
    );
  };

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
          <span>关键问题列表</span>
          <Tag color="volcano">{issues.length}</Tag>
        </div>
      }
      size="small"
      loading={loading}
    >
      {issues.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 0', 
          color: '#999' 
        }}>
          <ExclamationCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <div>暂无关键问题</div>
        </div>
      ) : (
        <div style={{ maxHeight, overflowY: 'auto' }}>
          <List
            itemLayout="vertical"
            dataSource={issues}
            renderItem={renderIssueItem}
            size="small"
          />
        </div>
      )}
    </Card>
  );
};

export default CriticalIssuesList;