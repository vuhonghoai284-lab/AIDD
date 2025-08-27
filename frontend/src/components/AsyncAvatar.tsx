import React, { useState, useEffect, useRef } from 'react';
import { Avatar } from 'antd';
import { UserOutlined } from '@ant-design/icons';

interface AsyncAvatarProps {
  src?: string;
  alt?: string;
  size?: number | 'small' | 'default' | 'large';
  icon?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  timeout?: number;
  fallbackDelay?: number; // 失败后多久显示fallback
}

/**
 * 异步头像组件 - 极简版本，专注于不阻塞页面渲染
 * 1. 立即渲染默认头像，0阻塞
 * 2. 后台异步加载，成功后替换
 * 3. 失败时保持默认头像
 */
const AsyncAvatar: React.FC<AsyncAvatarProps> = ({
  src,
  alt,
  size,
  icon = <UserOutlined />,
  className,
  style,
  timeout = 800,
  fallbackDelay = 100,
  ...props
}) => {
  const [imgSrc, setImgSrc] = useState<string | undefined>(undefined);
  const loadingRef = useRef<boolean>(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 清理之前的加载
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (!src) {
      setImgSrc(undefined);
      return;
    }

    // 标记开始加载
    loadingRef.current = true;

    // 使用 requestIdleCallback 或 setTimeout 延迟加载，确保不阻塞主渲染
    const startLoading = () => {
      if (!loadingRef.current) return;

      const img = new Image();
      
      const cleanup = () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        img.onload = null;
        img.onerror = null;
      };

      img.onload = () => {
        if (loadingRef.current) {
          setImgSrc(src);
        }
        cleanup();
      };

      img.onerror = () => {
        // 加载失败时，保持默认状态
        cleanup();
      };

      // 设置超时
      timeoutRef.current = setTimeout(() => {
        cleanup();
      }, timeout);

      // 开始加载
      img.src = src;
    };

    // 使用 requestIdleCallback 在浏览器空闲时加载
    if ('requestIdleCallback' in window) {
      requestIdleCallback(startLoading, { timeout: fallbackDelay });
    } else {
      // 降级到 setTimeout
      setTimeout(startLoading, fallbackDelay);
    }

    // 清理函数
    return () => {
      loadingRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [src, timeout, fallbackDelay]);

  return (
    <Avatar 
      src={imgSrc} // 如果imgSrc为undefined，Avatar会自动显示icon
      icon={icon}
      alt={alt}
      size={size}
      className={className}
      style={style}
      {...props}
    />
  );
};

export default AsyncAvatar;