/**
 * TaskList 后台刷新功能测试
 * 验证修复后的刷新机制不会影响用户操作
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import TaskList from '../TaskList';
import { taskAPI } from '../../api';

// Mock API
vi.mock('../../api', () => ({
  taskAPI: {
    getTasks: vi.fn(),
    deleteTask: vi.fn(),
    retryTask: vi.fn(),
    downloadReport: vi.fn(),
  },
}));

// Mock Ant Design message
vi.mock('antd', async () => {
  const antd = await vi.importActual('antd');
  return {
    ...antd as any,
    message: {
      error: vi.fn(),
      success: vi.fn(),
      warning: vi.fn(),
    },
  };
});

const mockTasks = [
  {
    id: 1,
    title: '测试任务1',
    status: 'processing',
    progress: 50,
    file_name: 'test1.pdf',
    file_size: 1024,
    created_at: '2024-01-01T00:00:00',
    created_by_name: '测试用户',
    created_by_type: 'normal_user',
  },
  {
    id: 2,
    title: '测试任务2',
    status: 'completed',
    progress: 100,
    file_name: 'test2.pdf',
    file_size: 2048,
    created_at: '2024-01-02T00:00:00',
    completed_at: '2024-01-02T01:00:00',
    processing_time: 3600,
    issue_count: 5,
    processed_issues: 3,
    created_by_name: '测试用户',
    created_by_type: 'normal_user',
  },
];

const renderTaskList = () => {
  return render(
    <BrowserRouter>
      <TaskList />
    </BrowserRouter>
  );
};

describe('TaskList 后台刷新功能', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(taskAPI.getTasks).mockResolvedValue(mockTasks);
    
    // Mock timers
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runAllTimers();
    vi.useRealTimers();
  });

  test('初始加载显示loading状态', async () => {
    renderTaskList();
    
    // 初始加载应该显示loading
    expect(screen.getByText('刷新')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(1);
    });
  });

  test('后台刷新不影响表格交互性', async () => {
    renderTaskList();
    
    // 等待初始加载完成
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 模拟用户正在操作表格
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    
    // 触发后台刷新（3秒后，因为有processing任务）
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    // 验证后台刷新不会导致表格不可用
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(2);
    });
    
    // 表格仍然可交互
    expect(table).not.toHaveAttribute('disabled');
    expect(screen.getByText('测试任务1')).toBeInTheDocument();
  });

  test('手动刷新显示loading状态', async () => {
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 点击手动刷新按钮
    const refreshButton = screen.getByText('刷新');
    fireEvent.click(refreshButton);
    
    // 手动刷新应该显示loading状态
    expect(refreshButton).toHaveAttribute('class', expect.stringContaining('ant-btn-loading'));
    
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(2);
    });
  });

  test('后台刷新指示器正常显示', async () => {
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 触发后台刷新
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    // 应该显示后台刷新指示器
    await waitFor(() => {
      expect(screen.getByText('更新中...')).toBeInTheDocument();
    });
    
    // 1秒后指示器消失
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    await waitFor(() => {
      expect(screen.queryByText('更新中...')).not.toBeInTheDocument();
    });
  });

  test('智能刷新频率：有processing任务时3秒刷新', async () => {
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 有processing任务，应该3秒刷新一次
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(2);
    });
    
    // 再过3秒
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(3);
    });
  });

  test('智能刷新频率：无processing任务时10秒刷新', async () => {
    // 模拟无processing任务
    const completedTasks = mockTasks.map(task => ({ ...task, status: 'completed' }));
    (taskAPI.getTasks as jest.Mock).mockResolvedValue(completedTasks);
    
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 无processing任务，3秒内不应该刷新
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    // 应该只有初始加载的1次调用
    expect(taskAPI.getTasks).toHaveBeenCalledTimes(1);
    
    // 10秒后应该刷新
    act(() => {
      jest.advanceTimersByTime(7000); // 总共10秒
    });
    
    await waitFor(() => {
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(2);
    });
  });

  test('删除操作后静默刷新', async () => {
    (taskAPI.deleteTask as jest.Mock).mockResolvedValue({});
    
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 点击删除按钮（需要找到删除按钮）
    const deleteButtons = screen.getAllByText('删除');
    fireEvent.click(deleteButtons[0]);
    
    await waitFor(() => {
      expect(taskAPI.deleteTask).toHaveBeenCalledWith(1);
      // 删除后应该触发静默刷新
      expect(taskAPI.getTasks).toHaveBeenCalledTimes(2);
    });
  });

  test('后台刷新失败不影响用户体验', async () => {
    renderTaskList();
    
    await waitFor(() => {
      expect(screen.getByText('测试任务1')).toBeInTheDocument();
    });
    
    // 模拟后台刷新失败
    (taskAPI.getTasks as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    // 触发后台刷新
    act(() => {
      jest.advanceTimersByTime(3000);
    });
    
    // 失败不应该显示错误消息给用户
    await waitFor(() => {
      expect(screen.queryByText(/加载任务列表失败/)).not.toBeInTheDocument();
    });
    
    // 页面内容仍然存在
    expect(screen.getByText('测试任务1')).toBeInTheDocument();
  });
});