"""
报告生成服务
"""
import os
from io import BytesIO
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# 可选依赖
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

from app.repositories.task import TaskRepository
from app.repositories.issue import IssueRepository
from app.models import Task, Issue
from app.services.task_permission_service import TaskPermissionService


class ReportService:
    """报告生成服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.issue_repo = IssueRepository(db)
        self.permission_service = TaskPermissionService(db)
    
    def check_download_permission_with_user(self, task_id: int, user) -> dict:
        """使用TaskPermissionService检查报告下载权限（推荐使用）
        
        Args:
            task_id: 任务ID
            user: 用户对象
            
        Returns:
            dict: 包含can_download和reason的字典
        """
        # 获取任务信息
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return {"can_download": False, "reason": "任务不存在"}
        
        # 检查基础访问权限
        if not self.permission_service.check_task_access(task_id, user, 'download'):
            return {"can_download": False, "reason": "无权限下载此任务的报告"}
        
        # 检查任务状态
        if task.status != "completed":
            return {"can_download": False, "reason": "任务尚未完成，请等待任务处理完成"}
        
        # 管理员特权：可以直接下载报告，无需等待问题处理完成
        if user.is_admin or user.is_system_admin:
            return {"can_download": True, "reason": "管理员权限"}
        
        # 检查问题处理状态
        total_issues = self.task_repo.count_issues(task_id)
        processed_issues = self.task_repo.count_processed_issues(task_id)
        
        if total_issues == 0:
            return {"can_download": True, "reason": "任务无问题，可以下载"}
        
        if processed_issues < total_issues:
            unprocessed_count = total_issues - processed_issues
            return {
                "can_download": False, 
                "reason": f"请先处理完所有问题才能下载报告。还有 {unprocessed_count} 个问题需要处理（共 {total_issues} 个问题）",
                "total_issues": total_issues,
                "processed_issues": processed_issues,
                "unprocessed_count": unprocessed_count
            }
        
        return {"can_download": True, "reason": "所有问题已处理完成"}
    
    def check_download_permission(self, task_id: int, user_id: int, is_admin: bool = False) -> dict:
        """检查报告下载权限（已废弃，建议使用 check_download_permission_with_user）
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            is_admin: 是否为管理员
            
        Returns:
            dict: 包含can_download和reason的字典
        """
        # 获取任务信息
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return {"can_download": False, "reason": "任务不存在"}
        
        # 管理员可以直接下载
        if is_admin:
            return {"can_download": True, "reason": "管理员权限"}
        
        # 检查任务所有权
        if task.user_id != user_id:
            return {"can_download": False, "reason": "无权限访问此任务"}
        
        # 检查任务状态
        if task.status != "completed":
            return {"can_download": False, "reason": "任务尚未完成，请等待任务处理完成"}
        
        # 检查问题处理状态
        total_issues = self.task_repo.count_issues(task_id)
        processed_issues = self.task_repo.count_processed_issues(task_id)
        
        if total_issues == 0:
            return {"can_download": True, "reason": "任务无问题，可以下载"}
        
        if processed_issues < total_issues:
            unprocessed_count = total_issues - processed_issues
            return {
                "can_download": False, 
                "reason": f"请先处理完所有问题才能下载报告。还有 {unprocessed_count} 个问题需要处理（共 {total_issues} 个问题）",
                "total_issues": total_issues,
                "processed_issues": processed_issues,
                "unprocessed_count": unprocessed_count
            }
        
        return {"can_download": True, "reason": "所有问题已处理完成"}
    
    def generate_excel_report(self, task_id: int) -> BytesIO:
        """生成Excel报告
        
        Args:
            task_id: 任务ID
            
        Returns:
            BytesIO: Excel文件的字节流
        """
        if not XLSXWRITER_AVAILABLE:
            raise ImportError("xlsxwriter未安装，无法生成Excel报告。请安装: pip install xlsxwriter")
        
        # 获取任务信息
        task = self.task_repo.get_by_id_with_relations(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 获取问题列表
        issues = self.issue_repo.get_by_task_id(task_id)
        
        # 创建Excel文件
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # 创建格式
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4CAF50',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8F5E8',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top',
            'text_wrap': True
        })
        
        severity_formats = {
            '严重': workbook.add_format({'bg_color': '#FFEBEE', 'border': 1, 'align': 'center'}),
            '重要': workbook.add_format({'bg_color': '#FFF3E0', 'border': 1, 'align': 'center'}),
            '一般': workbook.add_format({'bg_color': '#F3E5F5', 'border': 1, 'align': 'center'}),
            '轻微': workbook.add_format({'bg_color': '#E8F5E8', 'border': 1, 'align': 'center'})
        }
        
        # 创建工作表
        worksheet = workbook.add_worksheet('文档质量检测报告')
        
        # 设置列宽
        worksheet.set_column('A:A', 8)   # 序号
        worksheet.set_column('B:B', 15)  # 问题类型
        worksheet.set_column('C:C', 40)  # 问题描述
        worksheet.set_column('D:D', 15)  # 位置
        worksheet.set_column('E:E', 10)  # 严重程度
        worksheet.set_column('F:F', 30)  # 修改建议
        worksheet.set_column('G:G', 15)  # 用户反馈
        worksheet.set_column('H:H', 30)  # 反馈备注
        
        # 写入标题
        current_row = 0
        worksheet.merge_range(f'A{current_row + 1}:H{current_row + 1}', 
                             '文档质量检测报告', title_format)
        current_row += 1
        
        # 写入基本信息
        current_row += 1
        worksheet.write(current_row, 0, '任务信息', header_format)
        worksheet.merge_range(f'B{current_row + 1}:H{current_row + 1}', '', cell_format)
        
        current_row += 1
        info_data = [
            ('文档名称', task.file_info.original_name if task.file_info else '未知'),
            ('分析模型', task.ai_model.label if task.ai_model else '未知'),
            ('创建时间', task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''),
            ('完成时间', task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else '未完成'),
            ('问题总数', len(issues)),
            ('已处理问题', len([i for i in issues if i.feedback_type]))
        ]
        
        for label, value in info_data:
            worksheet.write(current_row, 0, label, cell_format)
            worksheet.merge_range(f'B{current_row + 1}:H{current_row + 1}', 
                                 str(value), cell_format)
            current_row += 1
        
        # 空行
        current_row += 1
        
        # 写入问题列表标题
        if issues:
            worksheet.write(current_row, 0, '问题详情列表', header_format)
            worksheet.merge_range(f'B{current_row + 1}:H{current_row + 1}', '', header_format)
            current_row += 1
            
            # 写入表头
            headers = ['序号', '问题类型', '问题描述', '位置', '严重程度', '修改建议', '用户反馈', '反馈备注']
            for col, header in enumerate(headers):
                worksheet.write(current_row, col, header, header_format)
            current_row += 1
            
            # 写入问题数据
            for idx, issue in enumerate(issues, 1):
                row_height = max(60, len(issue.description or '') // 20 * 15)
                worksheet.set_row(current_row, row_height)
                
                # 基本信息
                worksheet.write(current_row, 0, idx, cell_format)
                worksheet.write(current_row, 1, issue.issue_type or '', cell_format)
                worksheet.write(current_row, 2, issue.description or '', cell_format)
                worksheet.write(current_row, 3, issue.location or '', cell_format)
                
                # 严重程度（带颜色）
                severity = issue.severity or '一般'
                severity_format = severity_formats.get(severity, cell_format)
                worksheet.write(current_row, 4, severity, severity_format)
                
                worksheet.write(current_row, 5, issue.suggestion or '', cell_format)
                
                # 用户反馈
                feedback_text = {
                    'accept': '接受',
                    'reject': '拒绝',
                    'modify': '修改'
                }.get(issue.feedback_type, '未处理')
                
                feedback_color = {
                    'accept': '#E8F5E8',
                    'reject': '#FFEBEE',
                    'modify': '#FFF3E0'
                }.get(issue.feedback_type, '#F5F5F5')
                
                feedback_format = workbook.add_format({
                    'bg_color': feedback_color,
                    'border': 1,
                    'align': 'center'
                })
                
                worksheet.write(current_row, 6, feedback_text, feedback_format)
                worksheet.write(current_row, 7, issue.feedback_comment or '', cell_format)
                
                current_row += 1
        else:
            worksheet.merge_range(f'A{current_row + 1}:H{current_row + 1}', 
                                 '恭喜！本文档未发现任何质量问题。', 
                                 workbook.add_format({
                                     'bold': True,
                                     'align': 'center',
                                     'bg_color': '#E8F5E8',
                                     'font_color': '#2E7D32',
                                     'font_size': 12
                                 }))
        
        # 添加页脚
        current_row += 2
        worksheet.merge_range(f'A{current_row + 1}:H{current_row + 1}', 
                             f'报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                             workbook.add_format({
                                 'align': 'center',
                                 'font_size': 10,
                                 'italic': True
                             }))
        
        # 关闭工作簿
        workbook.close()
        output.seek(0)
        
        return output
    
    def get_report_filename(self, task_id: int) -> str:
        """获取报告文件名
        
        Args:
            task_id: 任务ID
            
        Returns:
            str: 报告文件名
        """
        task = self.task_repo.get_by_id_with_relations(task_id)
        if not task or not task.file_info:
            return f"质量检测报告_{task_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        # 从原始文件名中提取名称（去除扩展名）
        file_name = os.path.splitext(task.file_info.original_name)[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{file_name}_质量检测报告_{timestamp}.xlsx"