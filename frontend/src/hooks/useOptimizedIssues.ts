/**
 * 优化的问题管理Hook
 * 实现预加载、动画移除和无感知内容补充
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { taskAPI } from '../api';
import { Issue } from '../types';
import { message } from 'antd';

interface EnhancedIssue extends Issue {
  original_text?: string;
  user_impact?: string;
  reasoning?: string;
  context?: string;
  satisfaction_rating?: number;
  // 动画状态
  isRemoving?: boolean;
  isNew?: boolean;
}

interface UseOptimizedIssuesOptions {
  taskId: number;
  pageSize?: number;
  severityFilter?: string;
  statusFilter?: string;
}

interface UseOptimizedIssuesReturn {
  issues: EnhancedIssue[];
  loading: boolean;
  currentPage: number;
  totalIssues: number;
  hasNextPage: boolean;
  feedbackLoading: { [key: number]: boolean };
  // Actions
  handleQuickFeedback: (issueId: number, feedbackType: 'accept' | 'reject' | null, comment?: string) => Promise<void>;
  goToPage: (page: number) => Promise<void>;
  refreshCurrentPage: () => Promise<void>;
}

export function useOptimizedIssues({
  taskId,
  pageSize = 10,
  severityFilter = 'all',
  statusFilter = 'all'
}: UseOptimizedIssuesOptions): UseOptimizedIssuesReturn {
  
  // 状态管理
  const [issues, setIssues] = useState<EnhancedIssue[]>([]);
  const [preloadedIssues, setPreloadedIssues] = useState<EnhancedIssue[]>([]); // 预加载的下一页内容
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalIssues, setTotalIssues] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState<{ [key: number]: boolean }>({});
  
  // 缓存和状态引用
  const issuesCache = useRef<Map<string, EnhancedIssue[]>>(new Map());
  const removalTimeouts = useRef<Map<number, NodeJS.Timeout>>(new Map());
  
  // 生成缓存键
  const getCacheKey = useCallback((page: number) => {
    return `${taskId}-${page}-${pageSize}-${severityFilter}-${statusFilter}`;
  }, [taskId, pageSize, severityFilter, statusFilter]);
  
  // 加载指定页的问题
  const loadIssuesPage = useCallback(async (page: number): Promise<EnhancedIssue[]> => {
    const cacheKey = getCacheKey(page);
    
    // 检查缓存
    if (issuesCache.current.has(cacheKey)) {
      console.log(`🎯 使用缓存数据：第${page}页`);
      return issuesCache.current.get(cacheKey)!;
    }
    
    try {
      const params = {
        page,
        page_size: pageSize,
        search: undefined,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        issue_type: undefined,
        feedback_status: statusFilter !== 'all' ? (
          statusFilter === 'accepted' ? 'accept' :
          statusFilter === 'rejected' ? 'reject' :
          statusFilter === 'pending' ? 'unprocessed' : undefined
        ) : undefined,
        sort_by: 'id',
        sort_order: 'desc' as const
      };
      
      console.log(`🚀 加载第${page}页问题，参数:`, params);
      const response = await taskAPI.getTaskIssues(taskId, params);
      
      // 缓存结果
      issuesCache.current.set(cacheKey, response.items);
      
      return response.items;
    } catch (error) {
      console.error(`❌ 加载第${page}页问题失败:`, error);
      throw error;
    }
  }, [taskId, pageSize, severityFilter, statusFilter, getCacheKey]);
  
  // 预加载下一页内容
  const preloadNextPage = useCallback(async (currentPageNum: number) => {
    const nextPage = currentPageNum + 1;
    try {
      const nextPageIssues = await loadIssuesPage(nextPage);
      setPreloadedIssues(nextPageIssues);
      console.log(`📋 预加载第${nextPage}页完成，${nextPageIssues.length}个问题`);
    } catch (error) {
      console.warn(`⚠️ 预加载第${nextPage}页失败:`, error);
      setPreloadedIssues([]);
    }
  }, [loadIssuesPage]);
  
  // 加载当前页并预加载下一页
  const loadCurrentPageWithPreload = useCallback(async (page: number) => {
    setLoading(true);
    try {
      // 加载当前页
      const currentPageIssues = await loadIssuesPage(page);
      setIssues(currentPageIssues.map(issue => ({ ...issue, isNew: false })));
      setCurrentPage(page);
      
      // 更新分页信息
      const params = {
        page,
        page_size: pageSize,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        feedback_status: statusFilter !== 'all' ? (
          statusFilter === 'accepted' ? 'accept' :
          statusFilter === 'rejected' ? 'reject' :
          statusFilter === 'pending' ? 'unprocessed' : undefined
        ) : undefined,
        sort_by: 'id',
        sort_order: 'desc' as const
      };
      
      const response = await taskAPI.getTaskIssues(taskId, params);
      setTotalIssues(response.total);
      setHasNextPage(response.has_next);
      
      // 预加载下一页（异步，不阻塞当前页显示）
      if (response.has_next) {
        setTimeout(() => preloadNextPage(page), 100);
      }
      
    } finally {
      setLoading(false);
    }
  }, [taskId, pageSize, severityFilter, statusFilter, loadIssuesPage, preloadNextPage]);
  
  // 优化的反馈处理函数
  const handleQuickFeedback = useCallback(async (
    issueId: number, 
    feedbackType: 'accept' | 'reject' | null, 
    comment?: string
  ) => {
    setFeedbackLoading(prev => ({ ...prev, [issueId]: true }));
    
    try {
      // 1. 提交反馈
      if (feedbackType === null) {
        await taskAPI.submitFeedback(issueId, '', comment);
        message.success('已重置，可重新处理');
      } else {
        await taskAPI.submitFeedback(issueId, feedbackType, comment);
        message.success(
          feedbackType === 'accept' ? '已接受此问题' : '已拒绝此问题',
          1.5
        );
      }
      
      // 2. 立即更新本地状态（无需API调用）
      setIssues(prevIssues => 
        prevIssues.map(issue => {
          if (issue.id === issueId) {
            return {
              ...issue,
              user_feedback: feedbackType || undefined,
              feedback_comment: comment || issue.feedback_comment,
              isRemoving: true // 标记为正在移除
            };
          }
          return issue;
        })
      );
      
      // 3. 延迟移除动画效果
      const timeoutId = setTimeout(() => {
        let shouldUpdatePreloaded = false;
        let preloadedIssueToAdd: any = null;
        
        setIssues(prevIssues => {
          const newIssues = prevIssues.filter(issue => issue.id !== issueId);
          
          // 4. 如果当前页问题不足，从预加载内容补充
          if (newIssues.length < Math.min(pageSize, prevIssues.length) && preloadedIssues.length > 0) {
            const issueToAdd = preloadedIssues[0];
            newIssues.push({ ...issueToAdd, isNew: true });
            
            // 标记需要更新预加载状态
            shouldUpdatePreloaded = true;
            preloadedIssueToAdd = issueToAdd;
            
            console.log(`🔄 从预加载内容补充问题：${issueToAdd.id}`);
          }
          
          return newIssues;
        });
        
        // 分离预加载状态更新，避免状态更新竞态
        if (shouldUpdatePreloaded) {
          setPreloadedIssues(prev => prev.slice(1));
        }
        
        // 清理超时引用
        removalTimeouts.current.delete(issueId);
      }, 500); // 500ms动画时间
      
      // 存储超时引用，以便清理
      removalTimeouts.current.set(issueId, timeoutId);
      
      // 5. 清除相关缓存
      issuesCache.current.forEach((value, key) => {
        if (key.startsWith(`${taskId}-`)) {
          issuesCache.current.delete(key);
        }
      });
      
    } catch (error) {
      console.error('提交反馈失败:', error);
      message.error('操作失败');
      
      // 回滚本地状态
      setIssues(prevIssues => 
        prevIssues.map(issue => {
          if (issue.id === issueId) {
            return { ...issue, isRemoving: false };
          }
          return issue;
        })
      );
    } finally {
      setFeedbackLoading(prev => ({ ...prev, [issueId]: false }));
    }
  }, [taskId, pageSize]); // 移除preloadedIssues依赖避免频繁重新创建
  
  // 页面跳转
  const goToPage = useCallback(async (page: number) => {
    await loadCurrentPageWithPreload(page);
  }, [loadCurrentPageWithPreload]);
  
  // 刷新当前页
  const refreshCurrentPage = useCallback(async () => {
    // 清空缓存
    issuesCache.current.clear();
    await loadCurrentPageWithPreload(currentPage);
  }, [currentPage, loadCurrentPageWithPreload]);
  
  // 初始化和筛选条件变化
  useEffect(() => {
    // 清空缓存和预加载内容
    issuesCache.current.clear();
    setPreloadedIssues([]);
    
    // 重新加载第一页
    loadCurrentPageWithPreload(1);
  }, [loadCurrentPageWithPreload]);
  
  // 组件卸载时清理
  useEffect(() => {
    return () => {
      // 清理所有超时
      removalTimeouts.current.forEach(timeout => clearTimeout(timeout));
      removalTimeouts.current.clear();
      
      // 清空缓存
      issuesCache.current.clear();
    };
  }, []);
  
  return {
    issues,
    loading,
    currentPage,
    totalIssues,
    hasNextPage,
    feedbackLoading,
    handleQuickFeedback,
    goToPage,
    refreshCurrentPage
  };
}