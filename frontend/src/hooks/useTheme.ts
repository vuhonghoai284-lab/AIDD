import { useState, useEffect, createContext, useContext } from 'react';

// 主题配置类型
export interface ThemeConfig {
  name: string;
  icon: React.ReactNode;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
  };
  background: string;
  description: string;
}

export type ThemeType = 'ocean' | 'sunset' | 'forest' | 'galaxy';

// 主题上下文类型
interface ThemeContextType {
  currentTheme: ThemeType;
  themeConfig: ThemeConfig;
  setTheme: (theme: ThemeType) => void;
  themes: Record<ThemeType, ThemeConfig>;
}

// 创建主题上下文
export const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// 自定义Hook来使用主题
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// 获取保存的主题
export const getSavedTheme = (): ThemeType => {
  const savedTheme = localStorage.getItem('selectedTheme') as ThemeType;
  return savedTheme && ['ocean', 'sunset', 'forest', 'galaxy'].includes(savedTheme) 
    ? savedTheme 
    : 'ocean';
};

// 保存主题
export const saveTheme = (theme: ThemeType) => {
  localStorage.setItem('selectedTheme', theme);
};

// 应用主题样式到body元素
export const applyThemeToBody = (themeConfig: ThemeConfig) => {
  document.body.style.setProperty('--theme-primary', themeConfig.colors.primary);
  document.body.style.setProperty('--theme-secondary', themeConfig.colors.secondary);
  document.body.style.setProperty('--theme-accent', themeConfig.colors.accent);
  document.body.style.setProperty('--theme-background', themeConfig.background);
};