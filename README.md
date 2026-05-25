# IntelligentMarketingAssistant_AutoSend

基于 LangGraph + LangChain 的营销内容自动化工作流项目。

流程：

```text
输入产品/客户信息 -> 生成营销文案 -> 审核 -> Mock 发送邮件 -> 记录结果
```
终端根目录用:python -m pytest执行单元测试
## 技术栈

run_id / thread_id

run_id 用于业务审计和日志追踪，标识一次营销工作流运行；
thread_id 用于 LangGraph 运行线程标识，为后续 checkpointer、interrupt/resume 做准备。它们体现在 state、日志、数据库记录、LangGraph config 和测试断言中。

工作流依赖注入
工作流依赖注入是让 MarketingWorkflow 接收外部传入的 generator、reviewer、sender、recorder 等组件，而不是在内部强行创建真实依赖。这样生产环境可以用默认真实组件，测试环境可以注入 fake 组件，从而避免真实模型请求、真实发送和真实数据库写入，并能稳定覆盖关键分支。

| 技术 | 用途 |
|---|---|
| Python | 主开发语言 |
| LangGraph | 工作流编排、节点流转、条件分支 |
| LangChain | 大模型调用、Prompt 封装、工具封装 |
| langchain-openai | 通过 OpenAI-compatible 接口调用模型 |
| Pydantic | 输入、输出、审核结果、发送结果的数据校验 |
| python-dotenv | 读取 `.env` 环境变量 |
| SQLite | 本地保存发送记录 |
| logging | 分级日志记录 |
| pytest | 单元测试 |

## 环境变量

复制示例文件：

```bash
cp .env.example .env
```

然后修改 `.env`：

```env
MODEL_API_KEY=你的模型API_KEY
MODEL_BASE_URL=https://你的模型服务地址/v1
MODEL_NAME=deepseek-chat
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=60
WORKFLOW_MAX_RETRIES=2
DB_PATH=data/marketing_records.db
LOG_LEVEL=INFO
```

其中模型采样参数、审核重试上限和记录数据库路径均可通过环境变量调整。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行演示入口

```bash
python run_marketing_workflow.py
```

这是演示入口，会使用代码内置的一组产品/客户样例运行完整流程。

成功时，控制台只输出生成后的营销文案；审核结果、发送结果、记录 ID、异常信息会写入日志。

## 运行测试

```bash
pytest
```

## 说明

当前发送模块是 mock 实现，不会真实发送邮件。后续可替换为 SMTP、SendGrid、企业微信、CRM API 等真实渠道。
