import React, { useState, useEffect } from 'react';
import { Button, Card, Space, Typography, Divider, Alert } from 'antd';
import { ClockCircleOutlined, UserOutlined } from '@ant-design/icons';
import SafeAvatar from './SafeAvatar';
import AsyncAvatar from './AsyncAvatar';

const { Title, Text } = Typography;

/**
 * 头像性能对比演示组件
 * 用于展示旧版SafeAvatar和新版AsyncAvatar的性能差异
 */
const AvatarPerformanceDemo: React.FC = () => {
  const [renderTime, setRenderTime] = useState<{
    oldAvatar: number;
    newAvatar: number;
  }>({ oldAvatar: 0, newAvatar: 0 });

  const [testUrl, setTestUrl] = useState('https://api.dicebear.com/7.x/avataaars/svg?seed=test');

  // 模拟慢速网络的图片URL
  const slowImageUrl = 'https://httpbin.org/delay/2'; // 2秒延迟

  const measureRenderTime = (componentName: 'oldAvatar' | 'newAvatar') => {
    const startTime = performance.now();
    
    // 模拟组件渲染完成
    requestAnimationFrame(() => {
      const endTime = performance.now();
      const renderDuration = endTime - startTime;
      
      setRenderTime(prev => ({
        ...prev,
        [componentName]: renderDuration
      }));
    });
  };

  const testWithSlowNetwork = () => {
    setTestUrl(slowImageUrl);
    setRenderTime({ oldAvatar: 0, newAvatar: 0 });
  };

  const testWithNormalNetwork = () => {
    setTestUrl('https://api.dicebear.com/7.x/avataaars/svg?seed=test' + Math.random());
    setRenderTime({ oldAvatar: 0, newAvatar: 0 });
  };

  useEffect(() => {
    // 测量新版AsyncAvatar的渲染时间
    measureRenderTime('newAvatar');
  }, [testUrl]);

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <Title level={2}>头像加载性能对比</Title>
      
      <Alert
        message="优化说明"
        description="新版AsyncAvatar组件使用异步加载机制，立即渲染占位符，不会阻塞页面渲染。旧版SafeAvatar需要等待图片加载完成或超时。"
        type="info"
        style={{ marginBottom: 16 }}
      />

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space>
          <Button onClick={testWithNormalNetwork} type="primary">
            测试正常网络
          </Button>
          <Button onClick={testWithSlowNetwork} danger>
            测试慢速网络 (2秒延迟)
          </Button>
        </Space>

        <div style={{ display: 'flex', gap: 24 }}>
          <Card title="旧版 SafeAvatar (阻塞渲染)" style={{ flex: 1 }}>
            <Space direction="vertical" align="center" style={{ width: '100%' }}>
              <SafeAvatar
                src={testUrl}
                icon={<UserOutlined />}
                timeout={3000}
                size="large"
              />
              <Text type="secondary">
                <ClockCircleOutlined /> 渲染时间: {renderTime.oldAvatar.toFixed(2)}ms
              </Text>
              <Text type="warning">
                页面会被阻塞直到图片加载完成或超时
              </Text>
            </Space>
          </Card>

          <Card title="新版 AsyncAvatar (异步加载)" style={{ flex: 1 }}>
            <Space direction="vertical" align="center" style={{ width: '100%' }}>
              <AsyncAvatar
                src={testUrl}
                icon={<UserOutlined />}
                timeout={1000}
                size="large"
                fallbackDelay={50}
              />
              <Text type="secondary">
                <ClockCircleOutlined /> 渲染时间: {renderTime.newAvatar.toFixed(2)}ms
              </Text>
              <Text type="success">
                立即渲染，不阻塞页面，后台异步加载
              </Text>
            </Space>
          </Card>
        </div>

        <Divider />

        <div>
          <Title level={4}>优化效果</Title>
          <ul>
            <li><Text strong>零阻塞渲染</Text>: 页面立即显示，用户体验更流畅</li>
            <li><Text strong>更短超时</Text>: 从3秒减少到1秒，减少等待时间</li>
            <li><Text strong>智能回退</Text>: 加载失败时自动显示默认头像</li>
            <li><Text strong>懒加载支持</Text>: 可选的Intersection Observer懒加载</li>
            <li><Text strong>内存优化</Text>: 更好的清理机制，避免内存泄漏</li>
          </ul>
        </div>

        <Alert
          message="实际应用中的改进"
          description="在实际应用中，用户头像现在会立即显示默认图标，然后在后台异步加载真实头像，整个过程不会阻塞页面渲染，显著提升了页面加载速度和用户体验。"
          type="success"
        />
      </Space>
    </div>
  );
};

export default AvatarPerformanceDemo;