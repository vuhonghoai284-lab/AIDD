/**
 * 无限滚动Hook - 优化版本
 * 防止反复触发加载更多请求
 */
import { useEffect, useRef, useCallback } from 'react';

interface UseInfiniteScrollOptions {
  hasNextPage: boolean;
  loading: boolean;
  onLoadMore: () => Promise<void> | void;
  rootMargin?: string;
  threshold?: number;
  debounceMs?: number;
}

export function useInfiniteScroll({
  hasNextPage,
  loading,
  onLoadMore,
  rootMargin = '50px', // 减小rootMargin，避免过早触发
  threshold = 0.1,
  debounceMs = 1000 // 防抖时间，防止频繁触发
}: UseInfiniteScrollOptions) {
  const triggerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const lastTriggerTime = useRef<number>(0);
  const loadingRef = useRef<boolean>(false);

  // 防抖的加载更多函数
  const debouncedLoadMore = useCallback(async () => {
    const now = Date.now();
    
    // 防抖控制
    if (now - lastTriggerTime.current < debounceMs) {
      console.log(`🚦 无限滚动防抖：距离上次触发仅${now - lastTriggerTime.current}ms，跳过`);
      return;
    }

    // 防止并发触发
    if (loadingRef.current) {
      console.log('🚦 无限滚动：正在加载中，跳过');
      return;
    }

    // 检查是否还有更多数据
    if (!hasNextPage) {
      console.log('🚦 无限滚动：没有更多数据，跳过');
      return;
    }

    lastTriggerTime.current = now;
    loadingRef.current = true;

    try {
      console.log('♾️ 无限滚动：触发加载更多');
      await onLoadMore();
    } catch (error) {
      console.error('❌ 无限滚动加载更多失败:', error);
    } finally {
      loadingRef.current = false;
    }
  }, [hasNextPage, onLoadMore, debounceMs]);

  // 设置IntersectionObserver
  useEffect(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;

    // 清理之前的observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        
        if (entry.isIntersecting) {
          console.log('👁️ 无限滚动触发器进入视口');
          debouncedLoadMore();
        }
      },
      {
        root: null,
        rootMargin,
        threshold,
      }
    );

    observer.observe(trigger);
    observerRef.current = observer;

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [debouncedLoadMore, rootMargin, threshold]);

  // 更新loading状态引用
  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  return triggerRef;
}