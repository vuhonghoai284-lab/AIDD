/**
 * 文本格式化工具函数
 */

/**
 * 解码Unicode转义字符
 * @param text 包含Unicode转义字符的文本
 * @returns 解码后的文本
 */
export const decodeUnicode = (text: string): string => {
  try {
    // 处理 \uXXXX 格式的Unicode转义字符
    return text.replace(/\\u([0-9a-fA-F]{4})/g, (match, grp) => {
      return String.fromCharCode(parseInt(grp, 16));
    });
  } catch (error) {
    console.warn('Unicode解码失败:', error);
    return text;
  }
};

/**
 * 格式化JSON字符串为可读形式
 * @param jsonString JSON字符串
 * @returns 格式化后的JSON字符串
 */
export const formatJSON = (jsonString: string): string => {
  try {
    // 首先解码Unicode字符
    const decodedString = decodeUnicode(jsonString);
    
    // 尝试解析JSON并重新格式化
    const parsed = JSON.parse(decodedString);
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    console.warn('JSON格式化失败，返回解码后的原始文本:', error);
    return decodeUnicode(jsonString);
  }
};

/**
 * 智能格式化文本显示
 * @param text 原始文本
 * @param maxLineLength 最大行长度，超过此长度会自动换行
 * @returns 格式化后的文本
 */
export const formatTextDisplay = (text: string, maxLineLength: number = 80): string => {
  if (!text) return '';
  
  // 首先解码Unicode字符
  let formattedText = decodeUnicode(text);
  
  // 如果是JSON格式，尝试格式化
  if (formattedText.trim().startsWith('{') || formattedText.trim().startsWith('[')) {
    try {
      const parsed = JSON.parse(formattedText);
      formattedText = JSON.stringify(parsed, null, 2);
    } catch (error) {
      // 不是有效JSON，继续其他处理
    }
  }
  
  // 为过长的行添加换行
  const lines = formattedText.split('\n');
  const wrappedLines = lines.map(line => {
    if (line.length <= maxLineLength) {
      return line;
    }
    
    // 对于过长的行，在适当位置添加换行
    const words = line.split(' ');
    const wrappedLine: string[] = [];
    let currentLine = '';
    
    words.forEach(word => {
      if ((currentLine + word).length > maxLineLength && currentLine.length > 0) {
        wrappedLine.push(currentLine.trim());
        currentLine = word + ' ';
      } else {
        currentLine += word + ' ';
      }
    });
    
    if (currentLine.trim()) {
      wrappedLine.push(currentLine.trim());
    }
    
    return wrappedLine.join('\n');
  });
  
  return wrappedLines.join('\n');
};

/**
 * 为输入文本添加合理的换行和格式化
 * @param text 输入文本
 * @returns 格式化后的文本
 */
export const formatInputText = (text: string): string => {
  if (!text) return '';
  
  // 仅解码Unicode字符，保持原始文本结构
  return decodeUnicode(text);
};

/**
 * 检查文本是否可能是JSON格式
 * @param text 文本内容
 * @returns 是否为JSON格式
 */
export const isLikelyJSON = (text: string): boolean => {
  const trimmedText = text.trim();
  return (trimmedText.startsWith('{') && trimmedText.endsWith('}')) ||
         (trimmedText.startsWith('[') && trimmedText.endsWith(']'));
};

/**
 * 高亮显示文本中的特殊内容
 * @param text 原始文本
 * @returns 包含高亮标记的文本
 */
export const highlightSpecialContent = (text: string): string => {
  // 解码Unicode
  let highlightedText = decodeUnicode(text);
  
  // 高亮错误相关的文本
  highlightedText = highlightedText
    // 高亮严重程度
    .replace(/(严重|high|critical)/gi, '**$1**')
    .replace(/(一般|medium|moderate)/gi, '*$1*')
    .replace(/(轻微|low|minor)/gi, '_$1_')
    // 高亮错误类型
    .replace(/(错误|error|拼写|spelling|语法|grammar)/gi, '`$1`');
    
  return highlightedText;
};