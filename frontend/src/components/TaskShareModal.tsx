import React, { useState } from 'react';
import { Modal, Form, Select, Input, Button, message, Typography, Tag, Space, Alert } from 'antd';
import { ShareAltOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { UserSearchSelect } from './UserSearchSelect';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface TaskShareModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  taskId?: number;
  taskTitle?: string;
}

interface ShareRequest {
  shared_user_ids: number[];
  permission_level: string;
  share_comment?: string;
}

const PERMISSION_OPTIONS = [
  {
    value: 'full_access',
    label: '完全权限',
    description: '可查看、反馈、评论、评分、下载报告',
    color: 'green'
  },
  {
    value: 'feedback_only',
    label: '反馈权限',
    description: '可查看、反馈结果、评论、评分',
    color: 'blue'
  },
  {
    value: 'read_only',
    label: '只读权限',
    description: '仅可查看任务和报告内容',
    color: 'orange'
  }
];

export const TaskShareModal: React.FC<TaskShareModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  taskId,
  taskTitle
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);
  const [permissionLevel, setPermissionLevel] = useState('read_only');

  const handleSubmit = async (values: ShareRequest) => {
    if (!taskId) {
      message.error('任务ID缺失');
      return;
    }

    if (!values.shared_user_ids || values.shared_user_ids.length === 0) {
      message.error('请至少选择一个用户');
      return;
    }

    setLoading(true);
    
    try {
      const response = await fetch(`/api/task-share/${taskId}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(values)
      });

      if (response.ok) {
        const result = await response.json();
        message.success(`成功分享给 ${result.success_count} 个用户`);
        
        if (result.errors && result.errors.length > 0) {
          message.warning(`部分用户分享失败: ${result.errors.join(', ')}`);
        }
        
        form.resetFields();
        setSelectedUsers([]);
        setPermissionLevel('read_only');
        onSuccess();
      } else {
        const error = await response.json();
        message.error(error.detail || '分享失败');
      }
    } catch (error) {
      console.error('分享任务出错:', error);
      message.error('分享任务出错，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setSelectedUsers([]);
    setPermissionLevel('read_only');
    onCancel();
  };

  const selectedPermission = PERMISSION_OPTIONS.find(opt => opt.value === permissionLevel);

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShareAltOutlined />
          <span>分享任务</span>
        </div>
      }
      visible={visible}
      onCancel={handleCancel}
      footer={null}
      width={720}
      styles={{
        body: {
          maxHeight: '80vh',
          overflowY: 'auto',
          padding: '20px 24px 16px 24px'
        }
      }}
      maskClosable={false}
      destroyOnClose
    >
      <div style={{ marginBottom: 16 }}>
        <Text strong>任务: </Text>
        <Text>{taskTitle || `任务 #${taskId}`}</Text>
      </div>

      <Alert
        message="分享说明"
        description="分享后，被分享用户将能够根据设置的权限级别查看和操作此任务。您可以随时修改权限或撤销分享。"
        type="info"
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 20, fontSize: '12px' }}
        showIcon
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          permission_level: 'read_only'
        }}
        style={{ marginTop: 0 }}
      >
        <Form.Item
          name="shared_user_ids"
          label="选择要分享的用户"
          style={{ marginBottom: 20 }}
          rules={[
            { required: true, message: '请至少选择一个用户' },
            { type: 'array', min: 1, message: '请至少选择一个用户' }
          ]}
        >
          <UserSearchSelect
            value={selectedUsers}
            onChange={setSelectedUsers}
            placeholder="搜索用户名、显示名称进行分享"
            maxCount={20}
          />
        </Form.Item>

        <Form.Item
          name="permission_level"
          label="权限级别"
          style={{ marginBottom: 20 }}
          rules={[{ required: true, message: '请选择权限级别' }]}
        >
          <Select 
            onChange={setPermissionLevel}
            placeholder="选择权限级别"
            dropdownStyle={{ zIndex: 10001, maxHeight: '300px', overflow: 'auto' }}
            getPopupContainer={triggerNode => triggerNode.parentNode}
            optionLabelProp="label"
          >
            {PERMISSION_OPTIONS.map(option => (
              <Select.Option 
                key={option.value} 
                value={option.value}
                label={option.label}
              >
                <div style={{ 
                  padding: '8px 0', 
                  minHeight: '60px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 6, 
                    marginBottom: 4 
                  }}>
                    <Tag 
                      color={option.color} 
                      style={{ 
                        margin: 0, 
                        fontSize: '12px',
                        padding: '2px 8px',
                        borderRadius: '4px'
                      }}
                    >
                      {option.label}
                    </Tag>
                  </div>
                  <div style={{ 
                    fontSize: '11px', 
                    color: '#666', 
                    lineHeight: '1.4',
                    marginTop: '2px',
                    wordBreak: 'break-all'
                  }}>
                    {option.description}
                  </div>
                </div>
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {selectedPermission && (
          <div style={{ 
            marginBottom: 18, 
            padding: '6px 10px', 
            backgroundColor: '#f8f9fa', 
            borderRadius: 4,
            border: '1px solid #e9ecef'
          }}>
            <Space size="small" align="center" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: '12px' }}>已选权限:</Text>
              <Tag color={selectedPermission.color} style={{ margin: 0, fontSize: '11px' }}>
                {selectedPermission.label}
              </Tag>
            </Space>
            <div style={{ marginTop: 2 }}>
              <Text type="secondary" style={{ fontSize: '10px', lineHeight: 1.2 }}>
                {selectedPermission.description}
              </Text>
            </div>
          </div>
        )}

        <Form.Item
          name="share_comment"
          label="分享备注（可选）"
          style={{ marginBottom: 24 }}
        >
          <TextArea
            placeholder="添加分享说明或备注信息..."
            rows={2}
            maxLength={500}
            showCount
            style={{ fontSize: '13px', resize: 'none' }}
          />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0, textAlign: 'right', marginTop: 8 }}>
          <Space>
            <Button onClick={handleCancel}>
              取消
            </Button>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<ShareAltOutlined />}
            >
              确认分享
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};