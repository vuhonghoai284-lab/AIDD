import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { loginWithThirdParty } from '../services/authService';

/**
 * 第三方登录回调处理组件
 * 静默处理从第三方认证服务重定向回来的回调请求，不显示UI
 */
const CallbackHandler: React.FC = () => {
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // 防止React StrictMode导致的重复执行
    if (!isProcessing) {
      setIsProcessing(true);
      handleCallback();
    }
  }, [isProcessing]);

  // 全局锁机制：防止多个组件同时处理相同的授权码
  const acquireLock = (code: string): boolean => {
    const lockKey = `auth_processing_${code}`;
    const now = Date.now();
    const existingLock = sessionStorage.getItem(lockKey);
    
    if (existingLock) {
      const lockTime = parseInt(existingLock);
      // 如果锁存在且未过期（5分钟），返回false
      if (now - lockTime < 5 * 60 * 1000) {
        console.log('🔒 授权码正在被其他组件处理中，跳过');
        return false;
      }
    }
    
    // 获取锁
    sessionStorage.setItem(lockKey, now.toString());
    console.log('🔓 获取授权码处理锁成功');
    return true;
  };

  const releaseLock = (code: string) => {
    const lockKey = `auth_processing_${code}`;
    sessionStorage.removeItem(lockKey);
    console.log('🔓 释放授权码处理锁');
  };

  const handleCallback = async () => {
    try {
      // 1. 从URL中获取授权码
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const error = urlParams.get('error');
      const state = urlParams.get('state');

      // 2. 检查是否有错误参数
      if (error) {
        console.error('第三方认证失败:', error);
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: `第三方认证失败: ${error}` } 
        }));
        navigate('/login', { replace: true });
        return;
      }

      // 3. 检查是否有授权码
      if (!code) {
        console.error('未收到有效的授权码');
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: '未收到有效的授权码，请重新登录' } 
        }));
        navigate('/login', { replace: true });
        return;
      }

      console.log('收到第三方认证回调:', { code, state });

      // 4. 检查并获取处理锁
      if (!acquireLock(code)) {
        console.log('授权码正在处理中，跳过重复处理');
        navigate('/login', { replace: true });
        return;
      }

      // 触发登录开始事件，让LoginPage显示进度
      window.dispatchEvent(new CustomEvent('thirdPartyLoginStart'));

      // 5. 使用授权码进行登录
      const result = await loginWithThirdParty(code);

      if (result.success) {
        // 6. 登录成功，保存用户信息
        localStorage.setItem('user', JSON.stringify(result.user));
        localStorage.setItem('token', result.access_token || '');
        
        // 7. 显示成功消息
        message.success('第三方登录成功！');
        
        // 8. 释放锁
        releaseLock(code);
        
        // 9. 触发用户登录事件，通知App组件更新状态
        console.log('🚀 触发userLogin事件，通知App组件更新状态');
        window.dispatchEvent(new CustomEvent('userLogin', { 
          detail: { user: result.user, token: result.access_token } 
        }));
        
        // 10. 触发登录成功事件，让LoginPage显示成功状态
        window.dispatchEvent(new CustomEvent('thirdPartyLoginSuccess'));
        
        // 11. 等待React状态更新完成后再跳转
        console.log('⏳ 等待App组件确认状态更新完成...');
        
        let navigationTimeout: NodeJS.Timeout;
        let stateUpdateConfirmed = false;
        
        // 监听App组件发出的状态更新确认事件
        const handleStateUpdated = (event: CustomEvent) => {
          if (stateUpdateConfirmed) return; // 防止重复处理
          
          stateUpdateConfirmed = true;
          console.log('✅ 收到App组件状态更新确认，执行跳转');
          
          // 清除超时定时器
          if (navigationTimeout) {
            clearTimeout(navigationTimeout);
          }
          
          // 移除事件监听器
          window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
          
          // 执行跳转
          const preLoginLocation = sessionStorage.getItem('preLoginLocation');
          sessionStorage.removeItem('preLoginLocation');
          navigate(preLoginLocation || '/', { replace: true });
        };
        
        // 添加事件监听器
        window.addEventListener('userStateUpdated', handleStateUpdated as EventListener);
        
        // 优化：减少超时时间，但保持足够的容错空间
        navigationTimeout = setTimeout(() => {
          if (!stateUpdateConfirmed) {
            console.log('⚠️ 等待状态更新确认超时(1000ms)，强制跳转');
            window.removeEventListener('userStateUpdated', handleStateUpdated as EventListener);
            navigate('/', { replace: true });
          }
        }, 1000); // 1秒超时，平衡速度和可靠性

      } else {
        releaseLock(code);
        // 触发登录失败事件，让LoginPage处理UI显示
        window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
          detail: { error: result.message || '登录失败' } 
        }));
        navigate('/login', { replace: true });
      }

    } catch (error) {
      console.error('第三方登录回调处理失败:', error);
      
      // 发生异常时释放锁
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      if (code) releaseLock(code);
      
      // 触发登录失败事件，让LoginPage处理UI显示
      window.dispatchEvent(new CustomEvent('thirdPartyLoginError', { 
        detail: { error: '登录过程中发生错误，请稍后重试' } 
      }));
      navigate('/login', { replace: true });
    }
  };

  // 静默处理，不显示任何UI，直接返回null
  return null;
};

export default CallbackHandler;