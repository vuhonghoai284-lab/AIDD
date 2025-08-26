import React, { useState, useEffect } from 'react';
import { Card, Upload, Button, Input, message, Progress, Space, Tag, Select, Tooltip } from 'antd';
import { InboxOutlined, LoadingOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { taskAPI } from '../api';
import { useNavigate } from 'react-router-dom';
import config from '../config/index';

const { Dragger } = Upload;
const { Option } = Select;

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  taskId?: number;
  error?: string;
}

interface ModelInfo {
  index: number;
  label: string;
  description: string;
  provider: string;
  is_default: boolean;
}

const TaskCreate: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [creating, setCreating] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<number>(0);
  const navigate = useNavigate();

  useEffect(() => {
    // 获取可用模型列表
    const fetchModels = async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/models`);
        const data = await response.json();
        setModels(data.models);
        setSelectedModel(data.default_index);
      } catch (error) {
        console.error('Failed to fetch models:', error);
        message.warning('无法获取模型列表，将使用默认模型');
      }
    };
    fetchModels();
  }, []);

  const handleFilesSelect = (fileList: File[]) => {
    // 检查重复文件
    const existingFileNames = new Set(uploadedFiles.map(f => f.file.name));
    const newFiles: UploadedFile[] = [];
    
    fileList.forEach(file => {
      if (existingFileNames.has(file.name)) {
        message.warning(`文件 ${file.name} 已经添加`);
      } else {
        newFiles.push({
          file,
          status: 'pending',
        });
      }
    });
    
    if (newFiles.length > 0) {
      setUploadedFiles([...uploadedFiles, ...newFiles]);
      message.success(`已添加 ${newFiles.length} 个文件`);
    }
  };

  const handleRemoveFile = (index: number) => {
    const newFiles = [...uploadedFiles];
    newFiles.splice(index, 1);
    setUploadedFiles(newFiles);
  };

  const handleCreateTasks = async () => {
    const pendingFiles = uploadedFiles.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) {
      message.warning('没有需要处理的文件');
      return;
    }
    
    setCreating(true);
    
    // 判断是否使用批量API：文件数量超过3个时使用批量API，否则使用前端并发
    const useBatchAPI = pendingFiles.length > 3;
    
    if (useBatchAPI) {
      // 使用后端批量API（推荐方式）
      await handleBatchCreateTasks(pendingFiles);
    } else {
      // 使用前端并发创建（适用于少量文件）
      await handleConcurrentCreateTasks(pendingFiles);
    }
    
    setCreating(false);
  };

  const handleBatchCreateTasks = async (pendingFiles: UploadedFile[]) => {
    try {
      // 更新所有文件状态为创建中
      const tasks = [...uploadedFiles];
      pendingFiles.forEach((_, index) => {
        const taskIndex = tasks.findIndex(t => t.file === pendingFiles[index].file);
        if (taskIndex !== -1) {
          tasks[taskIndex].status = 'uploading';
        }
      });
      setUploadedFiles([...tasks]);
      
      message.info(`正在批量创建 ${pendingFiles.length} 个任务...`);
      
      // 调用批量创建API
      const createdTasks = await taskAPI.batchCreateTasks(
        pendingFiles.map(f => f.file), 
        selectedModel
      );
      
      // 更新成功的任务
      const updatedTasks = [...tasks];
      createdTasks.forEach(task => {
        const taskIndex = updatedTasks.findIndex(t => t.file.name === task.file_name);
        if (taskIndex !== -1) {
          updatedTasks[taskIndex].status = 'success';
          updatedTasks[taskIndex].taskId = task.id;
        }
      });
      setUploadedFiles(updatedTasks);
      
      message.success(`批量创建成功！共创建 ${createdTasks.length} 个任务`);
      
    } catch (error: any) {
      // 批量创建失败时，降级到前端并发创建
      message.warning('批量创建失败，正在使用逐个创建...');
      await handleConcurrentCreateTasks(pendingFiles);
    }
  };

  const handleConcurrentCreateTasks = async (pendingFiles: UploadedFile[]) => {
    const tasks = [...uploadedFiles];
    
    // 并发创建任务（不是串行）
    const createPromises = pendingFiles.map(async (pendingFile) => {
      const taskIndex = tasks.findIndex(t => t.file === pendingFile.file);
      if (taskIndex === -1) return;
      
      tasks[taskIndex].status = 'uploading';
      setUploadedFiles([...tasks]);
      
      try {
        const task = await taskAPI.createTask(pendingFile.file, undefined, selectedModel);
        tasks[taskIndex].status = 'success';
        tasks[taskIndex].taskId = task.id;
        setUploadedFiles([...tasks]);
        message.success(`${pendingFile.file.name} 创建任务成功`);
        return { success: true, fileName: pendingFile.file.name };
      } catch (error: any) {
        tasks[taskIndex].status = 'error';
        tasks[taskIndex].error = error.response?.data?.detail || '创建任务失败';
        setUploadedFiles([...tasks]);
        message.error(`${pendingFile.file.name} 创建任务失败: ${tasks[taskIndex].error}`);
        return { success: false, fileName: pendingFile.file.name };
      }
    });
    
    // 等待所有任务完成
    const results = await Promise.all(createPromises);
    const successCount = results.filter(r => r?.success).length;
    
    if (successCount > 0) {
      message.success(`并发创建完成！成功创建 ${successCount} 个任务`);
    }
  };

  const uploadProps = {
    name: 'files',
    multiple: true,
    accept: '.pdf,.docx,.md',
    beforeUpload: () => false, // 阻止自动上传
    onChange: (info: any) => {
      const fileList = info.fileList.map((item: any) => item.originFileObj).filter(Boolean);
      if (fileList.length > 0) {
        handleFilesSelect(fileList);
      }
    },
    showUploadList: false,
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag color="default">待处理</Tag>;
      case 'uploading':
        return <Tag color="blue">创建中</Tag>;
      case 'success':
        return <Tag color="green">已创建</Tag>;
      case 'error':
        return <Tag color="red">失败</Tag>;
      default:
        return null;
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Card title="创建文档测试任务" extra={
        <Button type="primary" onClick={() => navigate('/')}>
          返回列表
        </Button>
      }>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 模型选择 */}
          {models.length > 0 && (
            <div>
              <h3>选择分析模型</h3>
              <Select
                style={{ width: '100%' }}
                value={selectedModel}
                onChange={setSelectedModel}
                disabled={creating}
                optionLabelProp="label"
              >
                {models.map(model => (
                  <Option 
                    key={model.index} 
                    value={model.index}
                    label={`${model.label}${model.is_default ? ' (默认)' : ''}`}
                  >
                    <div style={{ padding: '4px 0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 500 }}>
                          {model.label}
                          {model.is_default && <Tag color="blue" style={{ marginLeft: 8 }}>默认</Tag>}
                        </span>
                        <Tooltip title={model.description}>
                          <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                        </Tooltip>
                      </div>
                      <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
                        {model.description} • 提供商: {model.provider}
                      </div>
                    </div>
                  </Option>
                ))}
              </Select>
            </div>
          )}

          <div>
            <h3>上传文档文件</h3>
            <p>支持的文件格式：PDF、Word (.docx)、Markdown (.md)，最大文件大小：10MB</p>
            <p style={{ color: '#52c41a', fontSize: '12px', marginTop: '4px' }}>
              💡 批量选择超过3个文件时将自动使用高性能批量创建模式
            </p>
            <Dragger {...uploadProps} disabled={creating}>
              <p className="ant-upload-drag-icon">
                {creating ? <LoadingOutlined /> : <InboxOutlined />}
              </p>
              <p className="ant-upload-text">
                {creating ? '正在创建任务...' : '点击或拖拽文件到此区域添加'}
              </p>
              <p className="ant-upload-hint">
                支持批量选择，选择文件后点击"创建任务"按钮开始处理
              </p>
            </Dragger>
          </div>

          {uploadedFiles.length > 0 && (
            <div>
              <h3>已选择的文件</h3>
              {uploadedFiles.map((item, index) => (
                <Card
                  key={index}
                  size="small"
                  style={{ marginBottom: 8 }}
                  bodyStyle={{ padding: '12px 16px' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>{item.file.name}</strong>
                      <span style={{ marginLeft: 8, color: '#666' }}>
                        ({formatFileSize(item.file.size)})
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {getStatusTag(item.status)}
                      {item.status === 'pending' && (
                        <Button 
                          size="small" 
                          type="text"
                          danger
                          onClick={() => handleRemoveFile(index)}
                          disabled={creating}
                        >
                          移除
                        </Button>
                      )}
                      {item.status === 'success' && item.taskId && (
                        <Button 
                          size="small" 
                          type="link"
                          onClick={() => navigate(`/task/${item.taskId}`)}
                        >
                          查看详情
                        </Button>
                      )}
                    </div>
                  </div>
                  {item.error && (
                    <div style={{ color: '#ff4d4f', marginTop: 4 }}>
                      错误：{item.error}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}

          {uploadedFiles.length > 0 && (
            <div style={{ textAlign: 'center', display: 'flex', gap: 16, justifyContent: 'center' }}>
              {uploadedFiles.filter(f => f.status === 'pending').length > 0 && (
                <Button 
                  type="primary" 
                  size="large" 
                  onClick={handleCreateTasks}
                  loading={creating}
                  disabled={creating}
                >
                  {uploadedFiles.filter(f => f.status === 'pending').length > 3 
                    ? `批量创建任务 (${uploadedFiles.filter(f => f.status === 'pending').length})` 
                    : `并发创建任务 (${uploadedFiles.filter(f => f.status === 'pending').length})`
                  }
                </Button>
              )}
              {uploadedFiles.filter(f => f.status === 'success').length > 0 && (
                <Button 
                  size="large" 
                  onClick={() => navigate('/')}
                >
                  查看所有任务
                </Button>
              )}
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default TaskCreate;