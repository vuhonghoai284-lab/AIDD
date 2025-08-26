"""
依赖检查和Mock系统
"""
def check_and_mock_dependencies():
    """检查依赖并创建必要的Mock"""
    import sys
    from unittest.mock import MagicMock
    
    # xlsxwriter Mock
    if 'xlsxwriter' not in sys.modules:
        xlsxwriter_mock = MagicMock()
        xlsxwriter_mock.Workbook = MagicMock()
        sys.modules['xlsxwriter'] = xlsxwriter_mock
        print("🔧 Mock xlsxwriter 已加载")
    
    # 其他可能缺失的依赖
    deps_to_mock = ['openpyxl', 'websockets']
    for dep in deps_to_mock:
        if dep not in sys.modules:
            sys.modules[dep] = MagicMock()
            print(f"🔧 Mock {dep} 已加载")

# 在导入时执行
check_and_mock_dependencies()
