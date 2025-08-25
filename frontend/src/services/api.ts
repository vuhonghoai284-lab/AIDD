// 导出api接口
import { taskAPI } from '../api';

export const getTaskDetail = taskAPI.getTaskDetail;
export const submitFeedback = taskAPI.submitFeedback;
export const downloadReport = taskAPI.downloadReport;
export const retryTask = taskAPI.retryTask;
export const getTasks = taskAPI.getTasks;
export const createTask = taskAPI.createTask;
export const deleteTask = taskAPI.deleteTask;
export const getTaskAIOutputs = taskAPI.getTaskAIOutputs;
export const getAIOutputDetail = taskAPI.getAIOutputDetail;

export default taskAPI;