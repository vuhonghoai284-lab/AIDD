# 任务列表频繁请求问题分析与优化

## 🚨 问题分析

### 后端观察到的现象
后端经常一次性收到很多查询任务列表的请求，造成服务器压力。

### 前端问题根源
通过代码分析，发现以下几个导致频繁请求的问题：

## 📋 主要问题

### 1. useCallback 依赖循环 🔄
**问题代码：**
```typescript
const loadTasks = useCallback(async (showLoading, forceRefresh) => {
  // ...
  setLastRefreshTime(now);
}, [lastRefreshTime]); // ❌ 依赖自己修改的状态
```

**问题：** 
- `lastRefreshTime` 被函数修改，又作为依赖
- 导致函数每次都重新创建
- 触发所有使用该函数的 useEffect

### 2. 定时器频繁重建 ⏰
**问题代码：**
```typescript
useEffect(() => {
  // 设置定时器...
}, [tasks.map(t => t.status).join(',')]); // ❌ 复杂依赖频繁变化
```

**问题：**
- 每次任务状态变化都重建定时器
- `tasks.map(t => t.status).join(',')` 计算复杂
- 导致定时器被过度重置

### 3. 多个并发请求源 📡
**问题：**
- 页面加载时立即请求
- 定时器周期性请求  
- 页面可见时立即请求
- 用户操作后立即请求
- 没有请求去重机制

### 4. 页面可见性检测过于敏感 👁️
**问题代码：**
```typescript
const handleVisibilityChange = () => {
  if (!document.hidden) {
    loadTasks(false, true); // ❌ 立即请求
  }
};
```

**问题：**
- 页面切换立即触发请求
- 可能与定时器请求冲突
- 没有防抖处理

## ✅ 解决方案

### 1. 修复依赖循环
```typescript
const loadTasks = useCallback(async (showLoading, forceRefresh) => {
  // 防止并发请求
  if (isRequestPending) return;
  
  // 防频繁访问使用闭包中的时间戳
  const now = Date.now();
  if (!forceRefresh && now - lastRefreshTime < 1000) return;
  
  // ... 请求逻辑
}, []); // ✅ 移除 lastRefreshTime 依赖
```

### 2. 优化定时器依赖
```typescript
useEffect(() => {
  const hasProcessingTasks = tasks.some(task => 
    task.status === 'processing' || task.status === 'pending'
  );
  const interval = hasProcessingTasks ? 5000 : 15000; // ✅ 增加间隔
  
  const timer = setInterval(backgroundRefresh, interval);
  return () => clearInterval(timer);
}, [
  backgroundRefresh, 
  tasks.filter(t => t.status === 'processing' || t.status === 'pending').length
]); // ✅ 只关注处理中任务数量
```

### 3. 全局请求去重机制
```typescript
// 全局请求去重
let pendingTaskRequest: Promise<Task[]> | null = null;

const makeRequest = async () => {
  if (!pendingTaskRequest) {
    pendingTaskRequest = taskAPI.getTasks();
  }
  
  try {
    const data = await pendingTaskRequest;
    return data;
  } finally {
    pendingTaskRequest = null; // 清除请求状态
  }
};
```

### 4. 页面可见性防抖处理
```typescript
let visibilityTimeout: NodeJS.Timeout | null = null;
const handleVisibilityChange = () => {
  if (!document.hidden) {
    if (visibilityTimeout) clearTimeout(visibilityTimeout);
    visibilityTimeout = setTimeout(() => {
      loadTasks(false, true);
    }, 1000); // ✅ 延迟1秒请求
  }
};
```

### 5. 并发请求防护
```typescript
const [isRequestPending, setIsRequestPending] = useState(false);

const makeRequest = async () => {
  if (isRequestPending) return; // ✅ 防止并发
  
  setIsRequestPending(true);
  try {
    // ... 请求逻辑
  } finally {
    setIsRequestPending(false);
  }
};
```

### 6. 操作后延迟刷新
```typescript
const handleDelete = async (taskId: number) => {
  await taskAPI.deleteTask(taskId);
  // ✅ 延迟刷新，避免立即请求
  setTimeout(() => backgroundRefresh(), 500);
};
```

## 📊 优化效果

### 请求频率优化
- **优化前：** 
  - 定时器：3秒/10秒间隔
  - 立即请求：页面切换、用户操作后立即
  - 并发请求：多个请求源同时发起

- **优化后：**
  - 定时器：5秒/15秒间隔  
  - 延迟请求：页面切换1秒后、操作0.5秒后
  - 请求去重：同一时间只有一个请求

### 请求次数预估
假设用户正常使用1小时：

**优化前：**
- 定时器：~200次 (3秒间隔，有处理中任务)
- 页面切换：~50次 
- 用户操作：~30次
- **总计：~280次/小时**

**优化后：**
- 定时器：~72次 (5秒间隔) 
- 页面切换：~20次 (防抖)
- 用户操作：~15次 (延迟+去重)
- **总计：~107次/小时**

**减少请求：~62%** 🎉

## 🔧 技术细节

### 内存使用优化
- 移除不必要的useCallback依赖
- 优化定时器重建频率
- 使用全局变量避免组件状态复杂化

### 用户体验保障
- 保持必要的实时性（处理中任务5秒刷新）
- 用户操作仍有及时反馈
- 页面切换仍能获取最新数据

### 错误处理
- 请求失败不影响后续请求
- 全局请求状态正确清理
- 开发环境保留调试信息

## 🧪 验证方法

### 开发环境测试
1. 打开浏览器开发者工具 Network 面板
2. 筛选 `/tasks/` 请求
3. 观察请求频率和时间间隔
4. 测试页面切换、用户操作等场景

### 后端监控
1. 监控 `/tasks/` 接口调用频率
2. 观察并发请求数量
3. 检查是否还有请求堆积

### 性能测试
1. 长时间开启页面，观察请求模式
2. 多个标签页同时打开测试
3. 网络慢时的请求行为

## 📝 总结

通过系统性的优化，我们解决了：
- ✅ useCallback 依赖循环问题
- ✅ 定时器频繁重建问题  
- ✅ 多个请求源并发问题
- ✅ 页面切换敏感性问题
- ✅ 缺乏请求去重机制问题

这些优化大幅减少了对后端的请求压力，同时保持了良好的用户体验。