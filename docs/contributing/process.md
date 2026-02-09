# 贡献指南

感谢你对 Nanobot 项目的兴趣！本指南将帮助你了解如何为项目做出贡献。

## 行为准则

- 保持友好和尊重
- 接受建设性的批评
- 关注对社区最有利的事情
- 尊重不同的观点和经验

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 先搜索现有的 issues，避免重复
2. 创建新 issue 并提供以下信息：
   - 问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息（操作系统、Python 版本等）
   - 相关日志或截图

### 提交代码

1. **Fork 仓库**
   ```bash
   git clone https://github.com/YOUR_USERNAME/nanobot.git
   cd nanobot
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **进行更改**
   - 编写清晰的代码
   - 添加测试（如果适用）
   - 更新文档（如果适用）

4. **运行测试**
   ```bash
   pytest tests/
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

6. **推送到你的 fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **创建 Pull Request**
   - 前往 GitHub 仓库
   - 点击 "New Pull Request"
   - 填写 PR 描述，说明更改内容和原因

## 提交信息规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 类型

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具/依赖更新

### 示例

```
feat: 添加多租户 Workspace 管理功能

- 实现 WorkspaceManager 类
- 支持创建/删除/查询工作空间
- 添加标准目录结构和模板文件

fix: 修复定时任务调度器并发问题

docs: 更新 API 文档中的认证说明

refactor: 优化用户配置管理器的文件操作
```

## 代码风格

### Python

- 遵循 [PEP 8](https://pep8.org/) 风格指南
- 使用 4 空格缩进
- 最大行长度 100 字符
- 使用有意义的变量名
- 添加 docstrings 到函数和类

### 示例

```python
def process_user_input(user_id: str, message: str) -> dict:
    """
    处理用户输入并返回响应。
    
    Args:
        user_id: 用户唯一标识
        message: 用户输入的消息
        
    Returns:
        包含响应内容和元数据的字典
        
    Raises:
        UserNotFoundError: 当用户不存在时
        InvalidInputError: 当输入无效时
    """
    if not user_id or not message:
        raise InvalidInputError("User ID and message are required")
    
    user = get_user(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    
    response = generate_response(user, message)
    
    return {
        "content": response,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
```

## 测试

### 编写测试

- 为新功能编写单元测试
- 测试边界情况和错误处理
- 使用有意义的测试名称

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_workspace.py

# 运行特定测试函数
pytest tests/test_workspace.py::test_create_workspace

# 显示详细输出
pytest -v

# 生成覆盖率报告
pytest --cov=nanobot --cov-report=html
```

## 文档

- 更新代码时同步更新相关文档
- 使用清晰的 Markdown 格式
- 添加代码示例说明用法
- 保持文档与代码同步

## 发布流程

1. 更新 `CHANGELOG.md`
2. 更新版本号（遵循 [Semantic Versioning](https://semver.org/)）
3. 创建 git tag
4. 推送到 GitHub
5. 创建 GitHub Release
6. 发布到 PyPI

## 联系方式

- **GitHub Issues**: [https://github.com/HKUDS/nanobot/issues](https://github.com/HKUDS/nanobot/issues)
- **Discord**: [https://discord.gg/MnCvHqpUGB](https://discord.gg/MnCvHqpUGB)
- **邮箱**: 查看 [COMMUNICATION.md](../../COMMUNICATION.md) 获取联系方式

## 致谢

感谢所有为 Nanobot 做出贡献的人！

<a href="https://github.com/HKUDS/nanobot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/nanobot" />
</a>

---

**快乐编码！** 🚀
