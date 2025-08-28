import React, { useState, useEffect } from 'react';
import { 
  Card, 
  List, 
  Avatar, 
  Tag, 
  Typography, 
  Space, 
  Button, 
  Empty, 
  Spin,
  message,
  Tooltip,
  Badge
} from 'antd';
import { 
  ShareAltOutlined, 
  EyeOutlined, 
  UserOutlined,
  CalendarOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './SharedTasks.css';

const { Title, Text, Paragraph } = Typography;

interface SharedUser {
  id: number;
  uid: string;
  display_name: string;
  avatar_url?: string;
}

interface TaskDetail {
  id: number;
  title: string;
  status: string;
  created_at: string;
  file_name: string;
  description?: string;
}

interface ShareInfo {
  id: number;
  permission_level: string;
  permission_name: string;
  permission_description: string;
  share_comment?: string;
  created_at: string;
  is_active: boolean;
}

interface SharedTask {
  task: TaskDetail;
  share_info: ShareInfo;
  shared_by: SharedUser;
}

const STATUS_CONFIG = {
  'pending': { color: 'blue', text: '等待中', icon: <ClockCircleOutlined /> },
  'processing': { color: 'orange', text: '处理中', icon: <ClockCircleOutlined /> },
  'completed': { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> },
  'failed': { color: 'red', text: '失败', icon: <ExclamationCircleOutlined /> }
};

const PERMISSION_CONFIG = {
  'full_access': { color: 'green', text: '完全权限' },
  'feedback_only': { color: 'blue', text: '反馈权限' },
  'read_only': { color: 'orange', text: '只读权限' }
};

export const SharedTasks: React.FC = () => {
  const [sharedTasks, setSharedTasks] = useState<SharedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSharedTasks();
  }, []);

  const fetchSharedTasks = async () => {
    try {
      const response = await fetch('/api/task-share/shared-with-me', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSharedTasks(data);
      } else {
        message.error('获取分享任务失败');
      }
    } catch (error) {
      console.error('获取分享任务出错:', error);
      message.error('获取分享任务出错');
    } finally {
      setLoading(false);
    }
  };

  const handleViewTask = (taskId: number) => {
    navigate(`/task/${taskId}`);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const renderTask = (item: SharedTask) => {
    const { task, share_info, shared_by } = item;
    const statusConfig = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG];
    const permissionConfig = PERMISSION_CONFIG[share_info.permission_level as keyof typeof PERMISSION_CONFIG];

    return (
      <List.Item
        key={`${task.id}-${share_info.id}`}
        className="shared-task-item"
        actions={[
          <Button
            key="view"
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewTask(task.id)}
          >
            查看任务
          </Button>
        ]}
      >
        <List.Item.Meta
          avatar={
            <Avatar 
              size={48}
              src={shared_by.avatar_url}
              icon={<UserOutlined />}
            />
          }
          title={
            <div className="task-title">
              <Space size="small">
                <Text strong>{task.title}</Text>
                <Tag color={statusConfig.color} icon={statusConfig.icon}>
                  {statusConfig.text}
                </Tag>
                <Tag color={permissionConfig.color}>
                  {permissionConfig.text}
                </Tag>
              </Space>
            </div>
          }
          description={
            <div className="task-meta">
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Text type="secondary">
                    <ShareAltOutlined /> 由 <Text strong>{shared_by.display_name}</Text> 分享
                  </Text>
                </div>
                
                <div>
                  <Space size="large">
                    <Text type="secondary">
                      <FileTextOutlined /> {task.file_name}
                    </Text>
                    <Text type="secondary">
                      <CalendarOutlined /> {formatDate(task.created_at)}
                    </Text>
                  </Space>
                </div>

                {share_info.share_comment && (
                  <div className="share-comment">
                    <Text type="secondary">
                      💬 {share_info.share_comment}
                    </Text>
                  </div>
                )}

                <div className="permission-info">
                  <Tooltip title={share_info.permission_description}>
                    <Tag color={permissionConfig.color} style={{ cursor: 'help' }}>
                      {share_info.permission_name}
                    </Tag>
                  </Tooltip>
                </div>
              </Space>
            </div>
          }
        />
      </List.Item>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text>加载分享任务中...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="shared-tasks-page">
      <Card>
        <div className="page-header">
          <Title level={2}>
            <ShareAltOutlined /> 分享给我的任务
          </Title>
          <Text type="secondary">
            查看其他用户分享给您的任务，并根据权限进行相应操作
          </Text>
        </div>

        {sharedTasks.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                暂无分享任务
                <br />
                <Text type="secondary">当其他用户分享任务给您时，它们会出现在这里</Text>
              </span>
            }
          />
        ) : (
          <>
            <div className="tasks-stats">
              <Space size="large">
                <Badge count={sharedTasks.length} showZero>
                  <Text strong>共享任务总数</Text>
                </Badge>
                <Badge 
                  count={sharedTasks.filter(t => t.task.status === 'completed').length} 
                  showZero 
                  color="green"
                >
                  <Text strong>已完成</Text>
                </Badge>
                <Badge 
                  count={sharedTasks.filter(t => t.share_info.permission_level === 'full_access').length} 
                  showZero 
                  color="blue"
                >
                  <Text strong>完全权限</Text>
                </Badge>
              </Space>
            </div>

            <List
              className="shared-tasks-list"
              dataSource={sharedTasks}
              renderItem={renderTask}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => 
                  `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }}
            />
          </>
        )}
      </Card>
    </div>
  );
};