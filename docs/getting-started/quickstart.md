# 快速开始

在 5 分钟内开始使用 Nanobot！

## 安装

### 方式一：使用 uv 安装（推荐）

```bash
uv tool install nanobot-ai
```

### 方式二：使用 pip 安装

```bash
pip install nanobot-ai
```

### 方式三：从源码安装

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

## 初始化

```bash
nanobot onboard
```

这会创建 `~/.nanobot/` 目录并生成默认配置文件。

## 配置 API 密钥

编辑 `~/.nanobot/config.json`，添加你的 API 密钥：

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

**获取 API 密钥：**
- [OpenRouter](https://openrouter.ai/keys)（推荐，支持多种模型）
- [Anthropic](https://console.anthropic.com)（Claude 官方）
- [OpenAI](https://platform.openai.com)（GPT 官方）

## 开始对话

### 单次对话

```bash
nanobot agent -m "你好，什么是 Nanobot？"
```

### 交互式对话

```bash
nanobot agent
```

进入交互模式后，直接输入消息即可对话。输入 `exit` 或 `quit` 退出。

## 下一步

- [完整安装指南](installation.md) - 了解详细的安装选项
- [配置说明](configuration.md) - 深入学习配置选项
- [系统架构](../architecture/overview.md) - 了解 Nanobot 的架构设计
- [CLI 参考](../api-reference/cli.md) - 查看所有可用的 CLI 命令

## 常见问题

**Q: 安装后找不到 `nanobot` 命令？**
A: 确保你的 Python 环境已添加到 PATH，或者使用 `python -m nanobot` 运行。

**Q: 配置文件中如何设置代理？**
A: 在 `config.json` 中添加 `proxy` 字段，格式为 `http://user:pass@host:port`。

**Q: 如何更新 Nanobot？**
A: 使用 `pip install --upgrade nanobot-ai` 或 `uv tool upgrade nanobot-ai`。

## 获取帮助

- [GitHub Issues](https://github.com/HKUDS/nanobot/issues)
- [Discord 社区](https://discord.gg/MnCvHqpUGB)
- [微信/飞书交流群](../../COMMUNICATION.md)
