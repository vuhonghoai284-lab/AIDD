/**
 * 任务列表自定义Hook - 优化版本
 * 解决反复触发分页查询和阻塞页面渲染问题
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { taskAPI } from '../api';
import { Task, PaginationParams, PaginatedResponse } from '../types';
import { message } from 'antd';

interface UseTaskListOptions {
  pageSize?: number;
  initialSearch?: string;
  initialStatus?: string;
}

interface UseTaskListReturn {
  tasks: Task[];
  loading: boolean;
  loadingMore: boolean;
  isBackgroundRefreshing: boolean;
  statisticsLoading: boolean;
  currentPage: number;
  totalTasks: number;
  hasNextPage: boolean;
  searchText: string;
  statusFilter: string;
  // Actions
  setSearchText: (text: string) => void;
  setStatusFilter: (status: string) => void;
  loadTasks: (options?: LoadTasksOptions) => Promise<void>;
  loadMoreTasks: () => Promise<void>;
  refreshTasks: () => Promise<void>;
  backgroundRefresh: () => Promise<void>;
  refreshStatistics: () => Promise<void>;
  goToPage: (page: number) => Promise<void>;
  // Stats
  statistics: TaskStatistics;
}

interface LoadTasksOptions {
  showLoading?: boolean;
  forceRefresh?: boolean;
  resetPage?: boolean;
  loadMore?: boolean;
  isSearchClear?: boolean;
  targetPage?: number;
}

interface TaskStatistics {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

// 防抖Hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 请求去重和缓存
class RequestManager {
  private static instance: RequestManager;
  private pendingRequests: Map<string, Promise<any>> = new Map();
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private cacheTimeout = 30000; // 30秒缓存

  static getInstance() {
    if (!RequestManager.instance) {
      RequestManager.instance = new RequestManager();
    }
    return RequestManager.instance;
  }

  private generateKey(params: PaginationParams): string {
    return JSON.stringify({
      page: params.page,
      page_size: params.page_size,
      search: params.search,
      status: params.status,
      sort_by: params.sort_by,
      sort_order: params.sort_order
    });
  }

  async request(params: PaginationParams, forceRefresh: boolean = false): Promise<PaginatedResponse<Task>> {
    const key = this.generateKey(params);

    // 检查缓存
    if (!forceRefresh) {
      const cached = this.cache.get(key);
      if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
        console.log('🎯 使用缓存数据:', key);
        return cached.data;
      }
    }

    // 检查是否有相同请求正在进行
    const existing = this.pendingRequests.get(key);
    if (existing) {
      console.log('🔄 复用进行中的请求:', key);
      return existing;
    }

    // 发起新请求
    console.log('🚀 发起新的API请求:', key);
    const request = taskAPI.getTasksPaginated(params)
      .then(result => {
        // 缓存结果
        this.cache.set(key, {
          data: result,
          timestamp: Date.now()
        });
        return result;
      })
      .finally(() => {
        // 清理请求记录
        this.pendingRequests.delete(key);
      });

    this.pendingRequests.set(key, request);
    return request;
  }

  clearCache() {
    this.cache.clear();
  }
}

export function useTaskList(options: UseTaskListOptions = {}): UseTaskListReturn {
  const {
    pageSize = 20,
    initialSearch = '',
    initialStatus = 'all'
  } = options;

  // 基础状态
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [isBackgroundRefreshing, setIsBackgroundRefreshing] = useState(false);
  const [statisticsLoading, setStatisticsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalTasks, setTotalTasks] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [realStatistics, setRealStatistics] = useState<TaskStatistics>({
    total: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0
  });
  
  // 搜索和过滤状态
  const [searchText, setSearchText] = useState(initialSearch);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  
  // 防抖搜索文本
  const debouncedSearchText = useDebounce(searchText, 300);
  
  // 内部状态
  const lastRefreshTime = useRef(0);
  const requestManager = useRef(RequestManager.getInstance());
  const abortControllerRef = useRef<AbortController | null>(null);

  // 统计数据 - 使用真实的数据库统计，而非当前页面数据
  const statistics = useMemo(() => {
    return realStatistics;
  }, [realStatistics]);

  // 处理中任务数量 - 用于动态调整刷新频率
  const processingTaskCount = useMemo(() => {
    return tasks.filter(t => t.status === 'processing' || t.status === 'pending').length;
  }, [tasks]);

  // 异步加载任务 - 使用useCallback避免重复创建
  const loadTasks = useCallback(async (options: LoadTasksOptions = {}) => {
    const {
      showLoading = true,
      forceRefresh = false,
      resetPage = true,
      loadMore = false,
      isSearchClear = false
    } = options;

    const now = Date.now();

    // 防抖控制 - 非强制刷新、非加载更多、非搜索清空时才应用防抖
    if (!forceRefresh && !loadMore && !isSearchClear && now - lastRefreshTime.current < 2000) {
      console.log('🚦 防抖跳过请求，距离上次请求过近');
      return;
    }

    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      if (showLoading && !loadMore) {
        setLoading(true);
      }
      if (loadMore) {
        setLoadingMore(true);
      }

      const page = loadMore ? currentPage + 1 : (options.targetPage || (resetPage ? 1 : currentPage));
      
      const params: PaginationParams = {
        page,
        page_size: pageSize,
        search: debouncedSearchText.trim() || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        sort_by: 'created_at',
        sort_order: 'desc'
      };

      console.log('📡 发起任务列表请求:', params);

      // 使用请求管理器发起异步请求
      const response = await requestManager.current.request(params, forceRefresh);

      if (loadMore) {
        // 加载更多：追加到现有列表
        setTasks(prev => [...prev, ...response.items]);
        setCurrentPage(page);
      } else {
        // 新的搜索或刷新：替换列表
        setTasks(response.items);
        setCurrentPage(page);
      }

      setTotalTasks(response.total);
      setHasNextPage(response.has_next);
      lastRefreshTime.current = now;

      console.log(`✅ 任务列表加载成功，第${page}页，获取到 ${response.items.length} 个任务，共 ${response.total} 个`);

    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('🔄 请求被取消');
        return;
      }
      console.error('❌ 加载任务列表失败:', error);
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
      setLoadingMore(false);
      abortControllerRef.current = null;
    }
  }, [currentPage, pageSize, debouncedSearchText, statusFilter]);

  // 加载更多任务
  const loadMoreTasks = useCallback(async () => {
    if (!hasNextPage || loadingMore || loading) {
      return;
    }
    console.log('📄 加载更多任务');
    await loadTasks({
      showLoading: false,
      forceRefresh: false,
      resetPage: false,
      loadMore: true
    });
  }, [hasNextPage, loadingMore, loading, loadTasks]);

  // 刷新任务列表
  const refreshTasks = useCallback(async () => {
    console.log('🔄 手动刷新任务列表');
    // 清除缓存以获取最新数据
    requestManager.current.clearCache();
    await loadTasks({
      showLoading: true,
      forceRefresh: true,
      resetPage: true
    });
  }, [loadTasks]);

  // 后台静默刷新
  const backgroundRefresh = useCallback(async () => {
    // 检查页面可见性
    if (document.hidden) {
      console.log('📱 页面不可见，跳过后台刷新');
      return;
    }

    const now = Date.now();
    if (now - lastRefreshTime.current < 3000) {
      console.log('⏰ 距离上次刷新时间过短，跳过后台刷新');
      return;
    }

    setIsBackgroundRefreshing(true);
    
    try {
      console.log('🌙 开始后台静默刷新');
      
      // 并行刷新任务列表和统计数据，避免串行等待
      const promises = [
        loadTasks({
          showLoading: false,
          forceRefresh: true,
          resetPage: true
        }),
        loadRealStatistics(false) // 后台刷新统计数据，不显示loading
      ];
      
      // 使用allSettled避免一个请求失败影响另一个
      const results = await Promise.allSettled(promises);
      
      // 记录失败的请求
      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          const name = index === 0 ? '任务列表' : '统计数据';
          console.warn(`⚠️ 后台刷新${name}失败:`, result.reason);
        }
      });
      
    } catch (error) {
      console.warn('⚠️ 后台刷新失败:', error);
    } finally {
      // 延迟隐藏刷新指示器，给用户视觉反馈
      setTimeout(() => setIsBackgroundRefreshing(false), 1000);
    }
  }, [loadTasks]);

  // 获取真实统计数据（异步，防止阻塞页面）
  const loadRealStatistics = useCallback(async (showLoading: boolean = false) => {
    // 检查是否有认证token
    const token = localStorage.getItem('token');
    if (!token) {
      console.log('⚠️ 未登录，跳过统计数据获取');
      return;
    }
    
    if (showLoading) {
      setStatisticsLoading(true);
    }
    
    try {
      console.log('📊 开始异步获取统计数据...');
      
      // 使用Promise.race添加超时控制，防止请求阻塞
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Statistics request timeout')), 10000)
      );
      
      const statsPromise = taskAPI.getTaskStatistics();
      const stats = await Promise.race([statsPromise, timeoutPromise]);
      
      setRealStatistics(stats);
      console.log('📊 统计数据已更新:', stats);
    } catch (error: any) {
      console.warn('⚠️ 获取统计数据失败:', error);
      
      // 只在超时或网络错误时显示用户友好提示
      if (error.message?.includes('timeout') || error.message?.includes('Network')) {
        // 静默失败，保持现有数据
        console.log('📊 统计数据获取超时，保持现有数据');
      }
      // 不显示错误消息，避免过多提示
    } finally {
      if (showLoading) {
        setStatisticsLoading(false);
      }
    }
  }, []);
  
  // 刷新统计数据（用户主动操作）
  const refreshStatistics = useCallback(async () => {
    console.log('🔄 用户主动刷新统计数据');
    await loadRealStatistics(true);
  }, [loadRealStatistics]);

  // 页码跳转功能
  const goToPage = useCallback(async (page: number) => {
    console.log(`📄 跳转到第 ${page} 页`);
    await loadTasks({
      showLoading: true,
      forceRefresh: false,
      resetPage: false,
      targetPage: page
    });
  }, [loadTasks]);

  // 搜索和过滤变更时的处理 - 使用防抖后的搜索文本
  useEffect(() => {
    console.log('🔍 搜索或过滤条件变更，重新加载数据');
    const isSearchClear = debouncedSearchText.trim() === '';
    loadTasks({
      showLoading: true,
      forceRefresh: false,
      resetPage: true,
      isSearchClear
    });
  }, [debouncedSearchText, statusFilter, loadTasks]);

  // 智能后台刷新定时器
  useEffect(() => {
    const hasProcessingTasks = processingTaskCount > 0;
    const interval = hasProcessingTasks ? 10000 : 30000; // 有处理中任务时10秒，否则30秒

    console.log(`⏰ 设置智能刷新定时器: 处理中任务${processingTaskCount}个, 间隔${interval}ms`);

    const timer = setInterval(() => {
      backgroundRefresh();
    }, interval);

    return () => {
      console.log('🧹 清理刷新定时器');
      clearInterval(timer);
    };
  }, [backgroundRefresh, processingTaskCount]);

  // 页面可见性变化处理
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('👀 页面重新可见，触发刷新');
        setTimeout(() => backgroundRefresh(), 1000);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [backgroundRefresh]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // 初始化时异步加载统计数据（非阻塞）
  useEffect(() => {
    console.log('🔄 初始化异步加载统计数据');
    // 使用setTimeout确保不阻塞主线程渲染
    const timeoutId = setTimeout(() => {
      loadRealStatistics(false); // 初始化时不显示loading，避免闪烁
    }, 100);
    
    return () => clearTimeout(timeoutId);
  }, [loadRealStatistics]);

  return {
    tasks,
    loading,
    loadingMore,
    isBackgroundRefreshing,
    statisticsLoading,
    currentPage,
    totalTasks,
    hasNextPage,
    searchText,
    statusFilter,
    setSearchText,
    setStatusFilter,
    loadTasks,
    loadMoreTasks,
    refreshTasks,
    backgroundRefresh,
    refreshStatistics,
    goToPage,
    statistics
  };
}