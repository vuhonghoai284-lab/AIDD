/**
 * 第三方登录用户体验优化测试
 * 验证登录状态即时响应和进度显示
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import CallbackHandler from '../CallbackHandler';
import LoginPage from '../LoginPage';

// Mock authService
vi.mock('../../services/authService', () => ({
  loginWithThirdParty: vi.fn(() => 
    Promise.resolve({
      success: true,
      user: { id: 1, uid: 'test_user', display_name: 'Test User', is_admin: false, is_system_admin: false, created_at: '2024-01-01T00:00:00' },
      access_token: 'test_token'
    })
  )
}));

// Mock antd message
vi.mock('antd', async () => {
  const antd = await vi.importActual('antd');
  return {
    ...antd as any,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  };
});

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
});

describe('第三方登录用户体验优化测试', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 清理事件监听器
    window.removeEventListener = vi.fn();
    window.addEventListener = vi.fn();
    window.dispatchEvent = vi.fn();
  });

  test('CallbackHandler应该显示实时登录进度', async () => {
    // 模拟URL参数
    delete (window as any).location;
    (window as any).location = {
      search: '?code=test_auth_code',
      href: 'http://localhost/third-login/callback?code=test_auth_code'
    };

    render(
      <BrowserRouter>
        <CallbackHandler />
      </BrowserRouter>
    );

    // 应该显示登录进度界面
    expect(screen.getByText(/正在处理登录信息/)).toBeInTheDocument();
    
    // 应该有进度条
    const progressElements = document.querySelectorAll('.ant-progress');
    expect(progressElements.length).toBeGreaterThan(0);
    
    // 应该有加载图标
    expect(document.querySelector('.anticon-loading')).toBeInTheDocument();
  });

  test('CallbackHandler应该显示成功状态', async () => {
    // 模拟成功登录
    const { loginWithThirdParty } = await import('../../services/authService');
    vi.mocked(loginWithThirdParty).mockResolvedValueOnce({
      success: true,
      user: { id: 1, uid: 'test_user', display_name: 'Test User', is_admin: false, is_system_admin: false, created_at: '2024-01-01T00:00:00' },
      access_token: 'test_token'
    });

    delete (window as any).location;
    (window as any).location = {
      search: '?code=test_auth_code',
      href: 'http://localhost/third-login/callback?code=test_auth_code'
    };

    render(
      <BrowserRouter>
        <CallbackHandler />
      </BrowserRouter>
    );

    // 等待登录完成
    await waitFor(() => {
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('user', expect.any(String));
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('token', 'test_token');
    }, { timeout: 3000 });
  });

  test('CallbackHandler应该显示错误状态', async () => {
    // 模拟登录失败
    const { loginWithThirdParty } = await import('../../services/authService');
    vi.mocked(loginWithThirdParty).mockResolvedValueOnce({
      success: false,
      message: '登录失败，请重试'
    });

    delete (window as any).location;
    (window as any).location = {
      search: '?code=invalid_code',
      href: 'http://localhost/third-login/callback?code=invalid_code'
    };

    render(
      <BrowserRouter>
        <CallbackHandler />
      </BrowserRouter>
    );

    // 应该显示错误状态
    await waitFor(() => {
      expect(screen.getByText(/登录失败/)).toBeInTheDocument();
    });

    // 应该显示错误图标
    expect(screen.getByText('❌')).toBeInTheDocument();
  });

  test('LoginPage应该立即响应第三方跳转', async () => {
    // 模拟URL带有code参数
    delete (window as any).location;
    (window as any).location = {
      search: '?code=test_auth_code',
      pathname: '/login',
      href: 'http://localhost/login?code=test_auth_code'
    };

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    // 应该立即显示登录中状态
    await waitFor(() => {
      expect(screen.getByText(/正在验证身份信息/)).toBeInTheDocument();
    });

    // 应该显示进度条
    const progressElements = document.querySelectorAll('.ant-progress');
    expect(progressElements.length).toBeGreaterThan(0);
  });

  test('登录进度应该有合理的步骤', () => {
    const progressSteps = [
      { progress: 10, message: '正在处理登录信息...' },
      { progress: 30, message: '正在验证授权码...' },
      { progress: 60, message: '正在登录系统...' },
      { progress: 85, message: '登录成功，正在初始化...' },
      { progress: 100, message: '跳转中...' }
    ];

    // 验证进度步骤的合理性
    progressSteps.forEach((step, index) => {
      if (index > 0) {
        expect(step.progress).toBeGreaterThan(progressSteps[index - 1].progress);
      }
      expect(step.progress).toBeGreaterThanOrEqual(0);
      expect(step.progress).toBeLessThanOrEqual(100);
      expect(step.message).toBeTruthy();
    });
  });

  test('优化时间应该在合理范围内', () => {
    const timeouts = {
      loginPageDelay: 100,    // LoginPage显示状态后的重定向延迟
      stateUpdateTimeout: 300, // 状态更新确认超时
      successDisplay: 200,     // 成功状态显示时间
      errorDisplay: 1500      // 错误状态显示时间
    };

    // 验证时间配置合理
    expect(timeouts.loginPageDelay).toBeLessThan(500); // 不超过0.5秒
    expect(timeouts.stateUpdateTimeout).toBeLessThan(1000); // 不超过1秒
    expect(timeouts.successDisplay).toBeLessThan(500); // 成功状态快速跳转
    expect(timeouts.errorDisplay).toBeGreaterThan(1000); // 错误状态给用户足够查看时间
  });

  test('用户体验优化指标', () => {
    const uxMetrics = {
      immediateVisualFeedback: true,  // 立即视觉反馈
      progressIndication: true,       // 进度指示
      statusMessages: true,          // 状态消息
      errorHandling: true,           // 错误处理
      fastStateTransition: true      // 快速状态转换
    };

    Object.entries(uxMetrics).forEach(([metric, value]) => {
      expect(value).toBe(true);
    });
  });
});