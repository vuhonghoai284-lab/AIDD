import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { Avatar } from 'antd';
import SafeAvatar from '../SafeAvatar';
import { vi } from 'vitest';

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

describe('SafeAvatar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('显示默认图标当没有src时', () => {
    render(<SafeAvatar />);
    expect(document.querySelector('.anticon-user')).toBeInTheDocument();
  });

  it('成功加载图片时显示图片', async () => {
    render(<SafeAvatar src="https://example.com/success.jpg" />);
    
    // Fast forward timers to simulate image load
    vi.advanceTimersByTime(50);
    
    await waitFor(() => {
      expect(document.querySelector('img')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('图片加载失败时显示默认图标', async () => {
    render(<SafeAvatar src="https://example.com/error.jpg" />);
    
    // Fast forward timers to simulate image error
    vi.advanceTimersByTime(50);
    
    await waitFor(() => {
      expect(document.querySelector('.anticon-user')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('图片加载超时时显示默认图标', async () => {
    render(<SafeAvatar src="https://example.com/timeout.jpg" timeout={1000} />);
    
    // Fast forward to trigger timeout
    vi.advanceTimersByTime(1100);
    
    await waitFor(() => {
      expect(document.querySelector('.anticon-user')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('显示加载状态', () => {
    render(<SafeAvatar src="https://example.com/loading.jpg" />);
    
    // Initially shows loading state (icon with opacity)
    const avatar = document.querySelector('.ant-avatar');
    expect(avatar).toBeInTheDocument();
  });

  it('传递其他props到Avatar组件', () => {
    render(<SafeAvatar size="large" className="custom-avatar" />);
    
    const avatar = document.querySelector('.ant-avatar');
    expect(avatar).toHaveClass('custom-avatar');
    expect(avatar).toHaveClass('ant-avatar-lg');
  });
});