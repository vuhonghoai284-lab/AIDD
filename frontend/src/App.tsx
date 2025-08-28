import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import { Layout, Menu, Dropdown, message } from 'antd';
import { FileAddOutlined, UnorderedListOutlined, UserOutlined, BarChartOutlined, ShareAltOutlined } from '@ant-design/icons';
import { flushSync } from 'react-dom';
import TaskCreate from './pages/TaskCreate';
import TaskList from './pages/TaskList';
import TaskDetailEnhanced from './pages/TaskDetailEnhanced';
import Analytics from './pages/Analytics';
import { SharedTasks } from './pages/SharedTasks';
import LoginPage from './pages/LoginPage';
import CallbackHandler from './pages/CallbackHandler';
import { getCurrentUser, logout, clearUserCache } from './services/authService';
import { User } from './types';
import { ThemeProvider } from './components/ThemeProvider';
import { useTheme } from './hooks/useTheme';
import AsyncAvatar from './components/AsyncAvatar';
import './App.css';

const { Header, Content } = Layout;

// 认证保护组件 - 修复时序问题版本
const ProtectedRoute: React.FC<{ children: React.ReactNode; user: User | null }> = ({ children, user }) => {
  const token = localStorage.getItem('token');
  const userString = localStorage.getItem('user');
  
  // 修复时序问题：优先使用React状态中的用户信息，其次使用localStorage
  const isAuthenticated = token && (user || userString);
  
  if (!isAuthenticated) {
    console.log('🔒 ProtectedRoute: 用户未认证，重定向到登录页面');
    console.log('   Token存在:', !!token);
    console.log('   React用户状态:', !!user);
    console.log('   localStorage用户:', !!userString);
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// 管理员权限保护组件
const AdminRoute: React.FC<{ children: React.ReactNode; user: User | null }> = ({ children, user }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (!user || (!user.is_admin && !user.is_system_admin)) {
    message.error('您没有权限访问此页面');
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

// 用户信息组件
const UserInfo: React.FC<{ user: User; onLogout: () => void }> = ({ user, onLogout }) => {
  const menuItems = [
    {
      key: 'logout',
      label: '退出登录',
      onClick: onLogout,
    },
  ];

  return (
    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
      <Dropdown menu={{ items: menuItems }} placement="bottomRight">
        <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <AsyncAvatar 
            src={user.avatar_url} 
            icon={<UserOutlined />}
            timeout={1000}
            fallbackDelay={50}
          />
          <span style={{ color: 'white', marginLeft: 8 }}>
            {user.display_name || user.uid}
            {user.is_admin && ' (管理员)'}
            {user.is_system_admin && ' (系统管理员)'}
          </span>
        </div>
      </Dropdown>
    </div>
  );
};

// 主题化Header组件
const ThemedHeader: React.FC<{ user: User | null; onLogout: () => void }> = ({ user, onLogout }) => {
  const { themeConfig } = useTheme();
  
  return (
    <Header 
      style={{ 
        background: themeConfig.background,
        borderBottom: 'none',
        position: 'fixed',
        zIndex: 1000,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
        <h1 style={{ 
          color: 'white', 
          margin: '0 20px 0 0',
          fontSize: '20px',
          fontWeight: 'bold',
          background: 'linear-gradient(45deg, #fff, #e8f4fd)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          textShadow: 'none'
        }}>
          AI文档测试系统
        </h1>
        <Menu 
          theme="dark" 
          mode="horizontal" 
          defaultSelectedKeys={['list']}
          style={{ 
            background: 'transparent',
            borderBottom: 'none',
            lineHeight: '64px'
          }}
          items={[
            {
              key: 'list',
              icon: <UnorderedListOutlined />,
              label: <Link to="/">任务列表</Link>
            },
            {
              key: 'create',
              icon: <FileAddOutlined />,
              label: <Link to="/create">创建任务</Link>
            },
            {
              key: 'shared',
              icon: <ShareAltOutlined />,
              label: <Link to="/shared">共享任务</Link>
            },
            ...(user?.is_admin ? [{
              key: 'analytics',
              icon: <BarChartOutlined />,
              label: <Link to="/analytics">运营统计</Link>
            }] : [])
          ]}
        />
        {user && <UserInfo user={user} onLogout={onLogout} />}
      </div>
    </Header>
  );
};

// 主应用组件
const AppContent: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const initUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          message.error('获取用户信息失败');
          handleLogout();
        }
      }
      setLoading(false);
    };

    initUser();
  }, []);

  // 监听登录事件（来自LoginPage和CallbackHandler的自定义事件）
  const handleUserLoginEvent = useCallback((event: CustomEvent) => {
    const { user: loggedInUser, token } = event.detail;
    
    // 确保localStorage中的数据是最新的
    localStorage.setItem('user', JSON.stringify(loggedInUser));
    localStorage.setItem('token', token);
    
    // 使用flushSync强制同步更新React状态，避免异步延迟
    flushSync(() => {
      setUser(loggedInUser);
    });
    
    
    // 状态已同步更新，立即发送确认信号
    window.dispatchEvent(new CustomEvent('userStateUpdated', {
      detail: { 
        success: true, 
        user: loggedInUser,
        timestamp: Date.now()
      }
    }));
  }, []);

  // 监听storage变化，当登录状态改变时更新用户信息
  useEffect(() => {
    const handleStorageChange = async () => {
      const token = localStorage.getItem('token');
      if (token && !user) {
        try {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error('获取用户信息失败', error);
        }
      } else if (!token && user) {
        setUser(null);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    
    window.addEventListener('userLogin', handleUserLoginEvent as EventListener);
    
    // 优化的token检查函数，减少不必要的API调用
    const checkTokenAndUser = async () => {
      const token = localStorage.getItem('token');
      const userString = localStorage.getItem('user');
      
      // 如果有token和用户数据，且React状态中也有用户，跳过检查
      if (token && userString && user) {
        return;
      }
      
      if (token && userString) {
        // 如果有token和用户数据但React状态为空，优先使用localStorage数据
        if (!user) {
          try {
            const storedUser = JSON.parse(userString);
            setUser(storedUser);
            console.log('🔄 从localStorage恢复用户状态');
          } catch (error) {
            console.warn('解析localStorage中的用户数据失败:', error);
            // 只有在localStorage数据损坏时才从API获取
            try {
              const currentUser = await getCurrentUser();
              if (currentUser) {
                setUser(currentUser);
                localStorage.setItem('user', JSON.stringify(currentUser));
              }
            } catch (e) {
              console.error('获取用户信息失败:', e);
              localStorage.removeItem('token');
              localStorage.removeItem('user');
              clearUserCache();
            }
          }
        }
      } else if (!token && user) {
        // 没有token但用户状态存在，需要登出
        setUser(null);
        clearUserCache();
      } else if (token && !userString) {
        // 有token但没有用户数据，清除可能无效的token
        localStorage.removeItem('token');
        clearUserCache();
      }
    };

    // 立即执行一次检查
    checkTokenAndUser();

    // 定期检查token变化（降低频率避免过度请求）
    const checkTokenInterval = setInterval(checkTokenAndUser, 5000); // 从100ms改为5秒

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('userLogin', handleUserLoginEvent as EventListener);
      clearInterval(checkTokenInterval);
    };
  }, []); // 移除user依赖，避免重复注册事件监听器

  const handleLogout = () => {
    logout();
    setUser(null);
    navigate('/login');
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/third-login/callback" element={<CallbackHandler />} />
      <Route path="/*" element={
        <Layout style={{ minHeight: '100vh' }}>
          <ThemedHeader user={user} onLogout={handleLogout} />
          <Content style={{ marginTop: '64px', background: '#f8fafc', minHeight: 'calc(100vh - 64px)' }}>
            <Routes>
              <Route 
                path="/" 
                element={
                  <ProtectedRoute user={user}>
                    <TaskList />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/create" 
                element={
                  <ProtectedRoute user={user}>
                    <TaskCreate />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/task/:id" 
                element={
                  <ProtectedRoute user={user}>
                    <TaskDetailEnhanced />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/shared" 
                element={
                  <ProtectedRoute user={user}>
                    <SharedTasks />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/analytics" 
                element={
                  <AdminRoute user={user}>
                    <Analytics />
                  </AdminRoute>
                } 
              />
            </Routes>
          </Content>
        </Layout>
      } />
    </Routes>
  );
};

function App() {
  return (
    <ThemeProvider>
      <Router>
        <AppContent />
      </Router>
    </ThemeProvider>
  );
}

export default App;