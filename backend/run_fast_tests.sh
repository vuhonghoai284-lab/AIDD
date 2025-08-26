#!/bin/bash
# 快速测试执行脚本

echo "⚡ 执行快速测试套件..."

# 1. 冒烟测试 (< 30秒)
echo "💨 步骤 1/4: 冒烟测试"
python -m pytest \
    --tb=line \
    --disable-warnings \
    -q \
    --maxfail=1 \
    -x \
    tests/test_system_api.py::TestSystemAPI::test_root_endpoint \
    tests/test_model_initialization.py::TestModelInitialization::test_test_mode_models_config \
    tests/test_auth_api.py::TestAuthAPI::test_system_admin_login_success \
    || { echo "❌ 冒烟测试失败"; exit 1; }

# 2. 快速单元测试 (< 60秒)  
echo "🔥 步骤 2/4: 快速单元测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -q \
    --maxfail=3 \
    -m "unit and not slow and not integration" \
    tests/unit/ \
    || { echo "❌ 快速单元测试失败"; exit 1; }

# 3. 系统API测试 (< 30秒)
echo "🌐 步骤 3/4: 系统API测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -q \
    --maxfail=2 \
    tests/test_system_api.py \
    tests/test_model_initialization.py \
    || { echo "❌ 系统API测试失败"; exit 1; }

# 4. 认证相关测试 (< 45秒)
echo "🔐 步骤 4/4: 认证测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -q \
    --maxfail=2 \
    -m "auth and not slow" \
    || { echo "❌ 认证测试失败"; exit 1; }

echo "✅ 快速测试套件全部通过! 🎉"