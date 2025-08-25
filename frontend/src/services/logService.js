/**
 * WebSocket日志服务
 * 管理任务日志的WebSocket连接和实时更新
 */
class LogService {
  constructor() {
    this.websocket = null;
    this.currentTaskId = null;
    this.logs = new Map(); // 缓存各任务的日志
    this.listeners = new Map(); // 事件监听器
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // 初始重连延迟(ms)
    this.heartbeatTimer = null;
    this.heartbeatTimeout = null;
    this.reconnectTimer = null;
    this.isConnecting = false;
    this.shouldReconnect = true; // 是否应该自动重连
    this.connectionClosed = false; // 标记连接是否被主动关闭
  }

  /**
   * 连接到指定任务的WebSocket
   */
  connect(taskId, taskStatus) {
    // 如果已经连接到这个任务，不要重复连接
    if (this.currentTaskId === taskId && this.websocket && 
        this.websocket.readyState === WebSocket.OPEN) {
      console.log('Already connected to task:', taskId);
      return;
    }

    // 如果正在连接中，避免重复连接
    if (this.isConnecting && this.currentTaskId === taskId) {
      console.log('Already connecting to this task');
      return;
    }

    // 如果正在连接其他任务，先断开
    if (this.currentTaskId !== taskId && this.websocket) {
      this.disconnect(1000, 'Switching to another task');
    }

    this.currentTaskId = taskId;
    this.isConnecting = true;
    this.connectionClosed = false;
    this.shouldReconnect = true;

    // 如果任务已完成或失败，优先从API获取历史日志
    if (taskStatus === 'completed' || taskStatus === 'failed') {
      console.log('Task is completed/failed, loading history only...');
      this.shouldReconnect = false; // 已完成的任务不需要重连
      this.fetchHistory(taskId).then(data => {
        this.isConnecting = false;
        this.emit('connected', { taskId });
      }).catch(error => {
        console.error('Failed to load history:', error);
        this.isConnecting = false;
        this.emit('disconnected', { taskId });
      });
      return;
    }

    // 动态获取WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_BASE_URL?.replace(/^wss?:\/\//, '') || window.location.host;
    const wsUrl = `${protocol}//${host}/ws/task/${taskId}/logs`;
    console.log('Connecting to WebSocket:', wsUrl);

    try {
      this.websocket = new WebSocket(wsUrl);
      this.setupEventHandlers(taskId);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.isConnecting = false;
      if (this.shouldReconnect && !this.connectionClosed) {
        this.handleReconnect(taskId);
      }
    }
  }

  /**
   * 设置WebSocket事件处理器
   */
  setupEventHandlers(taskId) {
    if (!this.websocket) return;

    // 连接打开
    this.websocket.onopen = () => {
      console.log('WebSocket connected to task:', taskId);
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.emit('connected', { taskId });
      this.startHeartbeat();
    };

    // 接收消息
    this.websocket.onmessage = (event) => {
      try {
        // 处理心跳响应
        if (event.data === 'pong') {
          this.clearHeartbeatTimeout();
          return;
        }
        
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    // 连接关闭
    this.websocket.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.stopHeartbeat();
      this.isConnecting = false;
      this.emit('disconnected', { taskId, code: event.code, reason: event.reason });
      
      // 只有在非正常关闭且允许重连时才重连
      // 1000 = 正常关闭, 1001 = 端点离开
      const isNormalClose = event.code === 1000 || event.code === 1001;
      if (this.shouldReconnect && !isNormalClose && !this.connectionClosed) {
        this.handleReconnect(taskId);
      } else {
        // 重置重连计数
        this.reconnectAttempts = 0;
      }
    };

    // 连接错误
    this.websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };
  }

  /**
   * 处理接收到的消息
   */
  handleMessage(data) {
    const { type, task_id } = data;

    // 根据消息类型处理
    switch (type) {
      case 'connection':
        console.log('Connection established:', data);
        break;
      
      case 'status':
        // 任务状态更新
        this.emit('status', data);
        // 如果任务已完成，标记不再重连
        if (data.status === 'completed' || data.status === 'failed') {
          this.shouldReconnect = false;
        }
        break;
      
      case 'progress':
        // 进度更新消息，仅触发进度事件，不作为日志显示
        this.emit('progress', {
          taskId: task_id,
          progress: data.progress,
          stage: data.stage
        });
        break;
      
      case 'log':
      default:
        // 普通日志消息
        this.addLog(task_id, data);
        this.emit('log', data);
        
        // 如果是进度更新，单独触发进度事件
        if (data.level === 'PROGRESS') {
          this.emit('progress', {
            taskId: task_id,
            progress: data.progress,
            message: data.message
          });
        }
        break;
    }
  }

  /**
   * 添加日志到缓存
   */
  addLog(taskId, log) {
    if (!this.logs.has(taskId)) {
      this.logs.set(taskId, []);
    }
    
    const logs = this.logs.get(taskId);
    logs.push(log);
    
    // 限制缓存大小
    if (logs.length > 1000) {
      logs.shift();
    }
  }

  /**
   * 获取任务的所有日志
   */
  getLogs(taskId) {
    return this.logs.get(taskId) || [];
  }

  /**
   * 清除任务日志
   */
  clearLogs(taskId) {
    this.logs.delete(taskId);
  }

  /**
   * 处理重连
   */
  handleReconnect(taskId) {
    // 如果已经有重连定时器在运行，不要重复创建
    if (this.reconnectTimer) {
      return;
    }
    
    // 如果不应该重连，直接返回
    if (!this.shouldReconnect || this.connectionClosed) {
      return;
    }
    
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('reconnect_failed', { taskId });
      this.shouldReconnect = false;
      return;
    }

    this.reconnectAttempts++;
    // 使用指数退避，但最大延迟不超过30秒
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.emit('reconnecting', { 
      taskId, 
      attempt: this.reconnectAttempts,
      delay 
    });

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      // 检查是否仍然需要重连
      if (this.shouldReconnect && !this.connectionClosed) {
        this.connect(taskId);
      }
    }, delay);
  }

  /**
   * 心跳机制
   */
  startHeartbeat() {
    this.stopHeartbeat(); // 确保没有重复的心跳
    
    this.heartbeatTimer = setInterval(() => {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send('ping');
        
        // 设置心跳超时检测
        this.setHeartbeatTimeout();
      }
    }, 30000); // 每30秒发送一次心跳
  }

  setHeartbeatTimeout() {
    this.clearHeartbeatTimeout();
    
    this.heartbeatTimeout = setTimeout(() => {
      console.warn('Heartbeat timeout, closing connection');
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        // 心跳超时，可能是网络问题，触发重连
        this.websocket.close(4000, 'Heartbeat timeout');
      }
    }, 5000); // 5秒内没收到pong就认为连接有问题
  }

  clearHeartbeatTimeout() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearHeartbeatTimeout();
  }

  /**
   * 断开连接
   */
  disconnect(code = 1000, reason = 'Normal closure') {
    console.log('Disconnecting WebSocket:', reason);
    
    // 标记为主动关闭
    this.connectionClosed = true;
    this.shouldReconnect = false;
    
    // 清除所有定时器
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    // 关闭WebSocket连接
    if (this.websocket) {
      if (this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.close(code, reason);
      }
      this.websocket = null;
    }

    // 重置状态
    this.reconnectAttempts = 0;
    this.currentTaskId = null;
    this.isConnecting = false;
  }

  /**
   * 事件监听器管理
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * 从API获取历史日志
   */
  async fetchHistory(taskId) {
    try {
      // 动态获取API URL
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.host}/api`;
      const response = await fetch(`${apiBaseUrl}/tasks/${taskId}/logs/history`);
      if (!response.ok) {
        throw new Error('Failed to fetch log history');
      }
      
      const logs = await response.json();
      
      // 确保每个日志都有必要的字段
      const normalizedLogs = logs.map(log => ({
        timestamp: log.timestamp || new Date().toISOString(),
        level: log.level || 'INFO',
        module: log.module || 'system',
        stage: log.stage || null,
        message: log.message || '',
        progress: log.progress || null,
        extra_data: log.extra_data || {}
      }));
      
      // 添加到缓存
      normalizedLogs.forEach(log => this.addLog(taskId, log));
      
      // 触发日志事件
      normalizedLogs.forEach(log => this.emit('log', log));
      
      return { logs: normalizedLogs };
    } catch (error) {
      console.error('Error fetching history:', error);
      throw error;
    }
  }
}

// 导出单例
const logService = new LogService();
export default logService;