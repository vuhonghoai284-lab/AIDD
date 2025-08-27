import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Avatar, Spin } from 'antd';
import { UserOutlined } from '@ant-design/icons';

interface SafeAvatarProps {
  src?: string;
  alt?: string;
  size?: number | 'small' | 'default' | 'large';
  icon?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  timeout?: number; // 超时时间，默认1秒
  showLoading?: boolean; // 是否显示加载状态
  lazy?: boolean; // 是否懒加载，默认true
}

/**
 * 安全头像组件 - 异步加载，不阻塞页面渲染
 * 1. 立即渲染占位符，避免阻塞页面
 * 2. 后台异步加载头像图片
 * 3. 支持懒加载和超时控制
 * 4. 加载失败时自动回退到默认图标
 */
const SafeAvatar: React.FC<SafeAvatarProps> = ({
  src,
  alt,
  size,
  icon = <UserOutlined />,
  className,
  style,
  timeout = 1000, // 默认1秒超时，更短避免长时间等待
  showLoading = true,
  lazy = true,
  ...props
}) => {
  const [imgSrc, setImgSrc] = useState<string | undefined>(undefined);
  const [loadState, setLoadState] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const avatarRef = useRef<HTMLDivElement>(null);

  // 清理函数
  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    if (imgRef.current) {
      imgRef.current.onload = null;
      imgRef.current.onerror = null;
      imgRef.current = null;
    }

    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  }, []);

  // 异步加载图片的函数
  const loadImage = useCallback(async () => {
    if (!src || loadState === 'loading' || loadState === 'loaded') {
      return;
    }

    setLoadState('loading');

    // 使用 Promise 包装图片加载，支持超时
    const loadImagePromise = new Promise<void>((resolve, reject) => {
      const img = new Image();
      imgRef.current = img;

      img.onload = () => {
        if (imgRef.current === img) {
          setImgSrc(src);
          setLoadState('loaded');
          resolve();
        }
      };

      img.onerror = () => {
        if (imgRef.current === img) {
          setLoadState('error');
          reject(new Error('Image load failed'));
        }
      };

      // 开始加载图片
      img.src = src;
    });

    // 设置超时Promise
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutRef.current = setTimeout(() => {
        setLoadState('error');
        cleanup();
        reject(new Error('Image load timeout'));
      }, timeout);
    });

    try {
      // 竞争加载：图片加载成功或超时，取较快的那个
      await Promise.race([loadImagePromise, timeoutPromise]);
      
      // 清除超时定时器
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    } catch (error) {
      console.warn(`头像加载失败: ${src}`, error);
    }
  }, [src, loadState, timeout, cleanup]);

  // 懒加载逻辑
  useEffect(() => {
    if (!src) {
      setImgSrc(undefined);
      setLoadState('idle');
      return;
    }

    if (!lazy) {
      // 不使用懒加载，立即开始加载
      loadImage();
      return;
    }

    // 使用 Intersection Observer 实现懒加载
    if ('IntersectionObserver' in window && avatarRef.current) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          const [entry] = entries;
          if (entry.isIntersecting) {
            loadImage();
            // 开始加载后就不需要再观察了
            observerRef.current?.disconnect();
          }
        },
        { threshold: 0.1 }
      );

      observerRef.current.observe(avatarRef.current);
    } else {
      // 不支持 Intersection Observer 时立即加载
      loadImage();
    }

    return cleanup;
  }, [src, lazy, loadImage, cleanup]);

  // 获取当前应该显示的内容
  const getAvatarContent = () => {
    // 成功加载的情况
    if (loadState === 'loaded' && imgSrc) {
      return (
        <Avatar 
          src={imgSrc}
          alt={alt}
          size={size}
          className={className}
          style={style}
          {...props}
        />
      );
    }

    // 加载中的情况
    if (loadState === 'loading' && showLoading) {
      return (
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <Avatar 
            icon={icon}
            size={size}
            className={className}
            style={{
              ...style,
              opacity: 0.7,
            }}
            {...props}
          />
          <div 
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(0, 0, 0, 0.1)',
              borderRadius: '50%',
            }}
          >
            <Spin size="small" />
          </div>
        </div>
      );
    }

    // 默认情况（未开始加载、加载失败、不显示加载状态）
    return (
      <Avatar 
        icon={icon}
        size={size}
        className={className}
        style={style}
        {...props}
      />
    );
  };

  return (
    <div ref={avatarRef} style={{ display: 'inline-block' }}>
      {getAvatarContent()}
    </div>
  );
};

export default SafeAvatar;