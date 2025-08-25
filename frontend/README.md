# AI资料测试系统 - 前端

这是AI资料自主测试系统的前端应用，基于React + TypeScript + Vite构建，使用Ant Design作为UI组件库。

## 项目概述

本前端应用提供了一个现代化的Web界面，用于管理和监控文档质量检测任务。系统包含用户认证、任务管理、实时日志查看、数据分析等功能模块。

## 技术栈

### 核心框架
- **React 18** - 前端框架
- **TypeScript** - 类型安全的JavaScript
- **Vite** - 快速构建工具

### UI与交互
- **Ant Design 5** - 企业级UI设计语言和组件库
- **React Router DOM 6** - 客户端路由管理
- **Axios** - HTTP客户端库

### 开发工具
- **Vite** - 开发服务器和构建工具
- **ESLint** - 代码质量检查
- **TypeScript** - 静态类型检查

## 项目结构

```
frontend/
├── public/                     # 静态资源
│   └── index.html             # HTML模板
├── src/                       # 源代码
│   ├── components/            # 通用组件
│   │   ├── TaskLogs.jsx      # 任务日志组件
│   │   └── ThemeProvider.tsx # 主题提供器
│   ├── hooks/                # 自定义Hook
│   │   └── useTheme.ts       # 主题Hook
│   ├── pages/                # 页面组件
│   │   ├── Analytics.tsx     # 数据分析页面
│   │   ├── LoginPage.tsx     # 登录页面
│   │   ├── TaskCreate.tsx    # 任务创建页面
│   │   ├── TaskDetailEnhanced.tsx # 任务详情页面
│   │   └── TaskList.tsx      # 任务列表页面
│   ├── services/             # 服务层
│   │   ├── api.ts           # API基础配置
│   │   ├── authService.ts   # 认证服务
│   │   └── logService.js    # 日志服务
│   ├── config/              # 配置文件
│   │   └── index.ts         # 应用配置
│   ├── App.tsx              # 主应用组件
│   ├── types.ts             # TypeScript类型定义
│   └── index.tsx            # 应用入口点
├── package.json             # 项目配置和依赖
├── tsconfig.json           # TypeScript配置
└── vite.config.ts          # Vite构建配置
```

## 功能模块

### 1. 用户认证系统
- **第三方登录** - 支持第三方OAuth认证
- **权限管理** - 基于角色的访问控制（普通用户/管理员）
- **会话管理** - JWT令牌认证和自动刷新

### 2. 任务管理
- **文件上传** - 支持PDF、DOCX、Markdown格式文档
- **任务创建** - 创建文档质量检测任务
- **任务列表** - 查看和管理所有任务
- **任务详情** - 查看详细的检测结果和问题列表

### 3. 质量检测
- **问题展示** - 展示AI检测到的文档问题
- **问题分类** - 按类型和严重程度分类显示
- **用户反馈** - 支持用户对检测结果进行反馈
- **满意度评分** - 1-5星评分系统

### 4. 实时监控
- **任务日志** - 实时显示任务处理日志
- **进度跟踪** - 显示任务处理进度
- **WebSocket连接** - 实时数据推送

### 5. 数据分析
- **统计面板** - 任务统计和趋势分析
- **性能指标** - 系统性能监控
- **数据可视化** - 图表展示分析结果

## 开发环境搭建

### 环境要求
- Node.js >= 14.0
- npm >= 6.0 或 yarn >= 1.22

### 安装依赖
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
# 或使用yarn
yarn install
```

### 环境配置

创建环境变量文件（可选）：
```bash
# .env.local
VITE_HOST=0.0.0.0
VITE_PORT=3000
VITE_PROXY_TARGET=http://localhost:8080
```

### 启动开发服务器
```bash
# 开发模式启动
npm run dev
# 或
yarn dev

# 应用将在 http://localhost:3000 启动
```

## 构建和部署

### 构建生产版本
```bash
# 构建生产版本
npm run build
# 或
yarn build

# 构建文件将输出到 dist/ 目录
```

### 预览生产构建
```bash
# 预览构建结果
npm run preview
# 或
yarn preview
```

### 部署选项

#### 1. 静态文件部署
将`dist/`目录的内容部署到任何静态文件服务器：
- Nginx
- Apache
- Caddy
- 云存储（如AWS S3、阿里云OSS）

#### 2. Docker部署
```dockerfile
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### 3. CDN部署
支持部署到各种CDN平台：
- Vercel
- Netlify
- GitHub Pages
- 阿里云CDN

## 配置说明

### 代理配置
开发环境下，前端通过Vite代理与后端API通信：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
})
```

### API配置
后端API基础配置：

```typescript
// src/services/api.ts
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api'  // 生产环境
  : '/api'; // 开发环境通过代理
```

### 认证配置
JWT令牌存储和管理：

```typescript
// localStorage中的键名
const TOKEN_KEY = 'token';
const USER_KEY = 'user';

// 自动添加认证头
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
```

## 开发指南

### 代码规范
- 使用TypeScript进行类型检查
- 遵循React Hooks最佳实践
- 使用函数式组件
- 组件命名使用PascalCase
- 文件命名使用camelCase

### 组件开发
```typescript
// 标准组件模板
import React from 'react';
import { ComponentProps } from '../types';

interface Props extends ComponentProps {
  // 定义组件属性
}

const MyComponent: React.FC<Props> = ({ ...props }) => {
  // 组件逻辑
  return (
    <div>
      {/* 组件内容 */}
    </div>
  );
};

export default MyComponent;
```

### 状态管理
- 使用React useState和useEffect
- 复杂状态使用useReducer
- 全局状态通过Context API
- 异步状态使用自定义Hook

### API调用
```typescript
// 使用async/await
const fetchData = async () => {
  try {
    const response = await api.get('/endpoint');
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    message.error('请求失败');
  }
};
```

## 主要页面说明

### 登录页面 (LoginPage)
- 第三方OAuth认证
- 自动重定向到原页面
- 错误处理和用户提示

### 任务列表 (TaskList)  
- 分页显示任务列表
- 状态筛选和搜索
- 批量操作支持
- 实时状态更新

### 任务创建 (TaskCreate)
- 文件上传和验证
- AI模型选择
- 表单验证和提交
- 进度显示

### 任务详情 (TaskDetailEnhanced)
- 问题分类显示
- 交互式问题反馈
- 满意度评分
- 任务日志查看

### 数据分析 (Analytics)
- 任务统计图表
- 性能指标监控
- 趋势分析
- 导出功能

## 主题和样式

### 主题切换
支持亮色/暗色主题切换：

```typescript
// 使用主题Hook
const { theme, toggleTheme } = useTheme();
```

### 样式组织
- 使用CSS Modules或styled-components
- 遵循BEM命名规范
- 响应式设计支持
- Ant Design主题定制

## 性能优化

### 代码分割
- 路由级别代码分割
- 组件懒加载
- 第三方库按需引入

### 缓存策略
- API响应缓存
- 静态资源缓存
- 浏览器缓存优化

### 打包优化
- Tree shaking
- 代码压缩
- 资源优化
- Bundle分析

## 常见问题

### Q: 如何修改后端API地址？
A: 修改`vite.config.ts`中的proxy配置，或设置环境变量`VITE_PROXY_TARGET`。

### Q: 如何添加新的页面？
A: 1) 在`src/pages/`创建组件 2) 在`App.tsx`添加路由 3) 更新导航菜单

### Q: 如何自定义Ant Design主题？
A: 在`vite.config.ts`中配置主题变量，或使用CSS变量覆盖。

### Q: 如何处理跨域问题？
A: 开发环境使用Vite代理，生产环境确保后端CORS配置正确。

### Q: 如何调试API请求？
A: 使用浏览器开发者工具，或在API服务中添加console.log。

## 部署checklist

- [ ] 构建生产版本无错误
- [ ] 检查环境变量配置
- [ ] 验证API连接正常
- [ ] 测试认证流程
- [ ] 检查静态资源路径
- [ ] 验证路由配置
- [ ] 测试核心功能
- [ ] 性能测试通过

## 贡献指南

1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 运行测试和类型检查
5. 提交Pull Request

## 许可证

本项目采用MIT许可证 - 查看LICENSE文件了解详情。

## 联系支持

如有问题或需要支持，请联系开发团队或提交Issue。