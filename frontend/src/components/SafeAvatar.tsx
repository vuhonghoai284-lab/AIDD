import React, { useState, useEffect, useRef } from 'react';
import { Avatar } from 'antd';
import { UserOutlined } from '@ant-design/icons';

interface SafeAvatarProps {
  src?: string;
  alt?: string;
  size?: number | 'small' | 'default' | 'large';
  icon?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  timeout?: number; // 超时时间，默认3秒
}

/**
 * 安全头像组件 - 支持超时和错误处理
 * 解决外部头像API（如dicebear.com）网络不通导致页面卡住的问题
 */
const SafeAvatar: React.FC<SafeAvatarProps> = ({
  src,
  alt,
  size,
  icon = <UserOutlined />,
  className,
  style,
  timeout = 3000, // 默认3秒超时
  ...props
}) => {
  const [imgSrc, setImgSrc] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    if (!src) {
      setImgSrc(undefined);
      setHasError(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setHasError(false);
    setImgSrc(undefined);

    // 创建一个新的图片对象来预加载图片
    const img = new Image();
    imgRef.current = img;

    // 设置超时定时器
    timeoutRef.current = setTimeout(() => {
      console.warn(`头像加载超时: ${src}`);
      setIsLoading(false);
      setHasError(true);
      if (imgRef.current) {
        imgRef.current.onload = null;
        imgRef.current.onerror = null;
        imgRef.current = null;
      }
    }, timeout);

    img.onload = () => {
      // 清除超时定时器
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      
      // 检查图片是否仍然有效（避免竞态条件）
      if (imgRef.current === img) {
        setImgSrc(src);
        setIsLoading(false);
        setHasError(false);
      }
    };

    img.onerror = () => {
      // 清除超时定时器
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      
      console.warn(`头像加载失败: ${src}`);
      if (imgRef.current === img) {
        setIsLoading(false);
        setHasError(true);
      }
    };

    // 开始加载图片
    img.src = src;

    // 清理函数
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      
      if (imgRef.current) {
        imgRef.current.onload = null;
        imgRef.current.onerror = null;
        imgRef.current = null;
      }
    };
  }, [src, timeout]);

  // 如果没有src或者加载出错，显示默认图标
  if (!src || hasError) {
    return (
      <Avatar 
        icon={icon}
        size={size}
        className={className}
        style={style}
        {...props}
      />
    );
  }

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <Avatar 
        icon={icon}
        size={size}
        className={className}
        style={{
          ...style,
          opacity: 0.6,
        }}
        {...props}
      />
    );
  }

  // 成功加载，显示图片
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
};

export default SafeAvatar;