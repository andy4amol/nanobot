# 安全最佳实践

本文档提供 Nanobot 安全配置和管理的核心指南。

## 报告安全漏洞

如果你发现了安全漏洞，请通过以下方式报告：

1. **不要** 公开创建 GitHub issue
2. 创建私有安全咨询或联系维护者
3. 包含以下信息：
   - 漏洞描述
   - 复现步骤
   - 潜在影响
   - 建议的修复方案

我们承诺在 48 小时内响应安全报告。

## API 密钥管理

**重要**：永远不要将 API 密钥提交到版本控制！

### 推荐做法

```bash
# 将配置文件设置为受限权限
chmod 600 ~/.nanobot/config.json
```

**推荐方案：**
- 将 API 密钥保存在 `~/.nanobot/config.json`（权限 0600）
- 考虑使用环境变量存储敏感密钥
- 生产环境使用 OS keyring/凭证管理器
- 定期轮换 API 密钥
- 开发和生产使用不同的 API 密钥

## 频道访问控制

**重要**：生产环境必须配置 `allowFrom` 白名单！

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["123456789", "987654321"]
    },
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

**安全提示：**
- 空 `allowFrom` 列表**允许所有人**访问（默认开放，适合个人使用）
- 从 `@userinfobot` 获取 Telegram 用户 ID
- WhatsApp 使用带国家码的完整手机号
- 定期审查访问日志，检查未授权访问

## Shell 命令执行安全

`exec` 工具可以执行 shell 命令。虽然已阻止危险命令模式，但仍需注意：

**应该做的：**
- 在 Agent 日志中审查所有工具使用
- 理解 Agent 运行的命令
- 使用权限受限的专用用户账户
- 永远不要以 root 身份运行 nanobot

**不应该做的：**
- 禁用安全检查
- 在未经仔细审查的系统上运行敏感数据

**已阻止的危险模式：**
- `rm -rf /` - 根文件系统删除
- Fork 炸弹
- 文件系统格式化 (`mkfs.*`)
- 原始磁盘写入
- 其他破坏性操作

## 文件系统访问

文件操作具有路径遍历保护，但仍需注意：

**应该做的：**
- 使用专用用户账户运行 nanobot
- 使用文件系统权限保护敏感目录
- 定期在日志中审计文件操作

**不应该做的：**
- 给予敏感文件不受限制的访问权限

## 网络安全

### API 调用
- 所有外部 API 调用默认使用 HTTPS
- 配置超时防止请求挂起
- 如有需要，使用防火墙限制出站连接

### WhatsApp Bridge
- Bridge 默认运行在 `localhost:3001`
- 如暴露到网络，使用适当的认证和 TLS
- 保持 `~/.nanobot/whatsapp-auth` 安全（模式 0700）

## 依赖安全

**重要**：保持依赖项更新！

```bash
# 检查易受攻击的依赖项
pip install pip-audit
pip-audit

# 更新到最新安全版本
pip install --upgrade nanobot-ai
```

对于 Node.js 依赖项（WhatsApp bridge）：
```bash
cd bridge
npm audit
npm audit fix
```

**重要提示：**
- 保持 `litellm` 更新到最新版本以获取安全修复
- 我们将 `ws` 更新到 `>=8.17.1` 以修复 DoS 漏洞
- 定期运行 `pip-audit` 或 `npm audit`
- 订阅 nanobot 及其依赖项的安全公告

## 生产部署

生产环境使用建议：

### 1. 隔离环境
```bash
# 在容器或 VM 中运行
docker run --rm -it python:3.11
pip install nanobot-ai
```

### 2. 使用专用用户
```bash
sudo useradd -m -s /bin/bash nanobot
sudo -u nanobot nanobot gateway
```

### 3. 设置适当权限
```bash
chmod 700 ~/.nanobot
chmod 600 ~/.nanobot/config.json
chmod 700 ~/.nanobot/whatsapp-auth
```

### 4. 启用日志记录
```bash
# 配置日志监控
tail -f ~/.nanobot/logs/nanobot.log
```

### 5. 使用速率限制
- 在 API 提供商上配置速率限制
- 监控使用情况的异常
- 在 LLM API 上设置支出限制

### 6. 定期更新
```bash
# 每周检查更新
pip install --upgrade nanobot-ai
```

## 开发 vs 生产

**开发环境：**
- 使用单独的 API 密钥
- 使用非敏感数据进行测试
- 启用详细日志记录
- 使用测试 Telegram bot

**生产环境：**
- 使用具有支出限制的专用 API 密钥
- 限制文件系统访问
- 启用审计日志记录
- 定期安全审查
- 监控异常活动

## 数据隐私

- **日志可能包含敏感信息** - 适当保护日志文件
- **LLM 提供商会看到你的提示** - 审查他们的隐私政策
- **聊天记录存储在本地** - 保护 `~/.nanobot` 目录
- **API 密钥是明文** - 生产环境使用 OS keyring

## 安全事件响应

如果你怀疑发生安全漏洞：

1. **立即撤销受损的 API 密钥**
2. **审查日志中的未授权访问**
   ```bash
   grep "Access denied" ~/.nanobot/logs/nanobot.log
   ```
3. **检查意外的文件修改**
4. **轮换所有凭证**
5. **更新到最新版本**
6. **向维护者报告事件**

## 安全功能

### 内置安全控制

✅ **输入验证**
- 文件操作的路径遍历保护
- 危险命令模式检测
- HTTP 请求的输入长度限制

✅ **认证**
- 基于白名单的访问控制
- 失败的认证尝试日志
- 默认开放（为生产环境配置 allowFrom）

✅ **资源保护**
- 命令执行超时（默认 60 秒）
- 输出截断（10KB 限制）
- HTTP 请求超时（10-30 秒）

✅ **安全通信**
- 所有外部 API 调用使用 HTTPS
- Telegram API 使用 TLS
- WhatsApp bridge 使用 WebSocket 安全

## 已知限制

⚠️ **当前安全限制：**

1. **无速率限制** - 用户可以发送无限消息（如需要自行添加）
2. **明文配置** - API 密钥以明文存储（生产环境使用 keyring）
3. **无会话管理** - 无自动会话过期
4. **有限的命令过滤** - 仅阻止明显的危险模式
5. **无审计追踪** - 有限的安全事件日志（根据需要增强）

## 安全清单

部署 nanobot 之前：

- [ ] API 密钥安全存储（不在代码中）
- [ ] 配置文件权限设置为 0600
- [ ] 为所有频道配置 `allowFrom` 列表
- [ ] 以非 root 用户运行
- [ ] 文件系统权限适当限制
- [ ] 依赖项更新到最新安全版本
- [ ] 日志监控安全事件
- [ ] 在 API 提供商上配置速率限制
- [ ] 备份和灾难恢复计划到位
- [ ] 自定义技能/工具的安全审查

## 更新日志

**最后更新**: 2026-02-03

查看最新安全更新和公告：
- GitHub Security Advisories: https://github.com/HKUDS/nanobot/security/advisories
- Release Notes: https://github.com/HKUDS/nanobot/releases

## 许可证

详见 LICENSE 文件。

## 相关文档

- [安全最佳实践](../security/best-practices.md) - 详细的安全配置指南
- [安全配置](../security/configuration.md) - 安全相关的配置项说明
- [数据隐私](../security/privacy.md) - 用户数据保护策略
- [生产部署](../security/deployment.md) - 生产环境部署指南
