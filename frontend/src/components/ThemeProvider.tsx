import React, { useState, useEffect } from 'react';
import { 
  CloudOutlined, 
  SunOutlined, 
  StarOutlined, 
  HeartOutlined 
} from '@ant-design/icons';
import { 
  ThemeContext, 
  ThemeType, 
  ThemeConfig, 
  getSavedTheme, 
  saveTheme, 
  applyThemeToBody,
  useTheme 
} from '../hooks/useTheme';

// 主题配置
const themes: Record<ThemeType, ThemeConfig> = {
  ocean: {
    name: '海洋',
    icon: <CloudOutlined />,
    colors: {
      primary: '#74b9ff',
      secondary: '#0984e3',
      accent: '#00cec9'
    },
    background: 'linear-gradient(135deg, #74b9ff 0%, #0984e3 50%, #74b9ff 100%)',
    description: '清新海洋风格'
  },
  sunset: {
    name: '日落',
    icon: <SunOutlined />,
    colors: {
      primary: '#fd79a8',
      secondary: '#e84393',
      accent: '#fdcb6e'
    },
    background: 'linear-gradient(135deg, #fd79a8 0%, #e84393 50%, #fd79a8 100%)',
    description: '温暖日落风格'
  },
  forest: {
    name: '森林',
    icon: <StarOutlined />,
    colors: {
      primary: '#00b894',
      secondary: '#00cec9',
      accent: '#55a3ff'
    },
    background: 'linear-gradient(135deg, #00b894 0%, #00cec9 50%, #55a3ff 100%)',
    description: '自然森林风格'
  },
  galaxy: {
    name: '星空',
    icon: <HeartOutlined />,
    colors: {
      primary: '#a29bfe',
      secondary: '#6c5ce7',
      accent: '#fd79a8'
    },
    background: 'linear-gradient(135deg, #a29bfe 0%, #6c5ce7 50%, #a29bfe 100%)',
    description: '梦幻星空风格'
  }
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

// 导出useTheme hook和themes配置
export { useTheme, themes };

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState<ThemeType>(() => getSavedTheme());

  const setTheme = (theme: ThemeType) => {
    setCurrentTheme(theme);
    saveTheme(theme);
    applyThemeToBody(themes[theme]);
  };

  // 初始化应用主题
  useEffect(() => {
    applyThemeToBody(themes[currentTheme]);
  }, [currentTheme]);

  const value = {
    currentTheme,
    themeConfig: themes[currentTheme],
    setTheme,
    themes
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};