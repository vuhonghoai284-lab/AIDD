#!/bin/bash
# 核心功能测试执行脚本 (排除慢速测试)

echo "🚀 执行核心功能测试..."

# 1. API接口测试 (< 90秒)
echo "🌐 步骤 1/5: API接口测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -v \
    --maxfail=5 \
    tests/test_*api*.py \
    --ignore=tests/stress/ \
    --ignore=tests/e2e/ \
    || { echo "❌ API测试失败"; exit 1; }

# 2. 任务相关测试 (不包含压力测试) (< 120秒)
echo "📋 步骤 2/5: 任务核心功能测试"  
python -m pytest \
    --tb=short \
    --disable-warnings \
    -v \
    --maxfail=3 \
    -m "task and not stress and not load and not e2e" \
    || { echo "❌ 任务测试失败"; exit 1; }

# 3. 用户相关测试 (< 60秒)
echo "👤 步骤 3/5: 用户功能测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -v \
    --maxfail=3 \
    -m "user and not slow" \
    || { echo "❌ 用户测试失败"; exit 1; }

# 4. 单元测试 (< 90秒)
echo "🧪 步骤 4/5: 单元测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -v \
    --maxfail=5 \
    -m "unit and not slow" \
    tests/unit/ \
    || { echo "❌ 单元测试失败"; exit 1; }

# 5. 集成测试 (排除慢速) (< 120秒)
echo "🔗 步骤 5/5: 集成测试"
python -m pytest \
    --tb=short \
    --disable-warnings \
    -v \
    --maxfail=3 \
    -m "integration and not slow and not e2e" \
    tests/integration/ \
    || { echo "❌ 集成测试失败"; exit 1; }

echo "✅ 核心功能测试全部通过! 🎉"
echo "📊 总耗时: 约 7-8分钟 (vs 原来的 15-20分钟)"