import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ command, mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    // 明确指定环境变量文件
    envDir: './',
    envPrefix: 'VITE_',
    server: {
      host: env.VITE_HOST || '0.0.0.0',  // 监听所有网络接口
      port: Number(env.VITE_PORT) || 3000,
      strictPort: false, // 如果端口被占用，自动尝试下一个端口
      proxy: {
        '/api': {
          target: env.VITE_PROXY_TARGET || 'http://localhost:8080',
          changeOrigin: true,
        }
      }
    },
    resolve: {
      extensions: ['.tsx', '.ts', '.jsx', '.js'],
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['node_modules', 'dist', 'e2e'],
      css: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        exclude: [
          'node_modules/',
          'src/test/',
          '**/*.d.ts',
          '**/*.config.*',
          'dist/',
          'src/main.tsx',
          'src/vite-env.d.ts'
        ],
        thresholds: {
          global: {
            branches: 75,
            functions: 85,
            lines: 80,
            statements: 80
          }
        }
      }
    }
  }
})