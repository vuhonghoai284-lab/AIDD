import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import AsyncAvatar from '../AsyncAvatar';
import { vi } from 'vitest';

// Mock requestIdleCallback
const mockRequestIdleCallback = vi.fn((callback, options) => {
  setTimeout(callback, options?.timeout || 0);
});

Object.defineProperty(window, 'requestIdleCallback', {
  writable: true,
  value: mockRequestIdleCallback,
});

// Mock Image constructor
class MockImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src = '';
  
  constructor() {
    // Simulate async loading
    setTimeout(() => {
      if (this.src.includes('success')) {
        this.onload?.();
      } else if (this.src.includes('error')) {
        this.onerror?.();
      }
      // For timeout test, neither onload nor onerror is called
    }, 10);
  }
}

// Mock global Image
(global as any).Image = MockImage;

describe('AsyncAvatar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('立即显示默认图标，不阻塞渲染', () => {
    const { container } = render(<AsyncAvatar src="https://example.com/loading.jpg" />);
    
    // 应该立即显示默认图标，不需要等待
    expect(container.querySelector('.anticon-user')).toBeInTheDocument();
    expect(container.querySelector('img')).not.toBeInTheDocument();
  });

  it('没有src时显示默认图标', () => {
    render(<AsyncAvatar />);
    expect(document.querySelector('.anticon-user')).toBeInTheDocument();
  });

  it('成功加载图片后替换默认图标', async () => {
    const { container } = render(<AsyncAvatar src="https://example.com/success.jpg" fallbackDelay={0} />);
    
    // 初始状态：显示默认图标
    expect(container.querySelector('.anticon-user')).toBeInTheDocument();
    
    // 快进到图片加载完成
    vi.advanceTimersByTime(50);
    
    await waitFor(() => {
      expect(container.querySelector('img')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('图片加载失败时保持默认图标', async () => {
    const { container } = render(<AsyncAvatar src="https://example.com/error.jpg" fallbackDelay={0} />);
    
    // 初始状态：显示默认图标
    expect(container.querySelector('.anticon-user')).toBeInTheDocument();
    
    // 快进到图片加载失败
    vi.advanceTimersByTime(50);
    
    // 等待一段时间，应该仍然显示默认图标
    await waitFor(() => {
      expect(container.querySelector('.anticon-user')).toBeInTheDocument();
      expect(container.querySelector('img')).not.toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('图片加载超时时保持默认图标', async () => {
    const { container } = render(<AsyncAvatar src="https://example.com/timeout.jpg" timeout={100} fallbackDelay={0} />);
    
    // 初始状态：显示默认图标
    expect(container.querySelector('.anticon-user')).toBeInTheDocument();
    
    // 快进到超时
    vi.advanceTimersByTime(150);
    
    await waitFor(() => {
      expect(container.querySelector('.anticon-user')).toBeInTheDocument();
      expect(container.querySelector('img')).not.toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('使用requestIdleCallback延迟加载', () => {
    render(<AsyncAvatar src="https://example.com/test.jpg" fallbackDelay={100} />);
    
    // 验证requestIdleCallback被调用
    expect(mockRequestIdleCallback).toHaveBeenCalledWith(
      expect.any(Function),
      { timeout: 100 }
    );
  });

  it('传递其他props到Avatar组件', () => {
    const { container } = render(<AsyncAvatar size="large" className="custom-avatar" />);
    
    const avatar = container.querySelector('.ant-avatar');
    expect(avatar).toHaveClass('custom-avatar');
    expect(avatar).toHaveClass('ant-avatar-lg');
  });

  it('src变化时重新加载', async () => {
    const { rerender, container } = render(<AsyncAvatar src="https://example.com/first.jpg" fallbackDelay={0} />);
    
    // 快进加载第一个图片
    vi.advanceTimersByTime(50);
    
    // 更改src
    rerender(<AsyncAvatar src="https://example.com/success.jpg" fallbackDelay={0} />);
    
    // 快进加载第二个图片
    vi.advanceTimersByTime(50);
    
    await waitFor(() => {
      expect(container.querySelector('img')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('组件卸载时正确清理资源', () => {
    const { unmount } = render(<AsyncAvatar src="https://example.com/test.jpg" />);
    
    // 卸载组件
    unmount();
    
    // 验证没有内存泄漏（通过检查定时器被清理）
    expect(vi.getTimerCount()).toBe(0);
  });
});