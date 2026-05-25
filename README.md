# AgentWorkflow - Intelligent Marketing Assistant AutoSend

基于 LangGraph 与 LangChain 的受控营销内容生成工作流 Demo，面向 B2B 营销场景。项目重点展示结构化生成、合规审核回路、失败留痕、组件替换和后续恢复执行的演进边界，而不是接入真实外部发送副作用。

## Workflow

```text
产品/客户信息 -> 生成营销文案 -> 规则审核 + LLM 审核
                                      | 通过
                                      v
                              Mock 发送 -> 记录结果
                                      ^
                                      |
                              审核建议驱动改写
```

## Highlights

- 使用 Pydantic 定义输入、营销内容、审核结果、发送结果和工作流状态。
- 使用 LangGraph 表达生成、审核、改写、发送和失败记录等条件流转。
- 采用规则审核与 LLM 语义审核组合，处理确定性风险和语义风险。
- 将 prompt 独立管理，并通过本地 JSON parser 与 Pydantic 校验模型输出。
- 集中管理模型参数、审核重试次数和 SQLite 数据库路径。
- 支持注入 generator、reviewer、sender 与 recorder，便于测试和替换实现。
- 为每次运行记录 `run_id` 与 `thread_id`，为后续 checkpoint 与 interrupt/resume 预留上下文。
- 发送模块为 mock 实现，不会真实发送邮件。

## Tech Stack

| 技术 | 用途 |
|---|---|
| Python | 主开发语言 |
| LangGraph | 工作流编排与条件分支 |
| LangChain / langchain-openai | OpenAI-compatible 模型调用 |
| Pydantic | 输入输出与状态校验 |
| SQLite | 本地保存执行记录 |
| pytest | 流程和配置测试 |

## Setup

建议使用 Python 3.11+。

```bash
pip install -r requirements.txt
cp .env.example .env
```

配置 `.env`：

```env
MODEL_API_KEY=replace-with-your-api-key
MODEL_BASE_URL=https://api.example.com/v1
MODEL_NAME=deepseek-chat
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=60
WORKFLOW_MAX_RETRIES=2
DB_PATH=data/marketing_records.db
LOG_LEVEL=INFO
```

## Run

演示入口使用内置的一组产品和客户样例运行完整流程：

```bash
python run_marketing_workflow.py
```

运行测试：

```bash
python -m pytest -q
```

## Scope

当前版本不实现真实发送、LangGraph checkpointer、人工审批暂停恢复或副作用幂等控制。`thread_id` 已贯穿运行上下文与记录层，用于说明后续向 durable execution 与 human-in-the-loop 工作流演进的路径。
