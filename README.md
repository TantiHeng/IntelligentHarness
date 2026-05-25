# AgentWorkflow-IntelligentMarketingAssistant_AutoSend-
用 LangGraph 实现了一个针对高副作用业务场景的受控 Agent 工作流，重点解决结构化生成、合规审核回路、失败留痕、组件可替换和后续恢复执行的演进边界。这是一个基于 LangGraph 和 LangChain 的受控营销内容生成工作流 Demo。它面向 B2B 营销场景，输入产品信息和客户画像后，由大模型生成营销文案，再经过规则审核和 LLM 语义审核；如果审核不通过，工作流会根据审核建议自动改写，审核通过后进入 mock 发送节点，并将运行结果记录到 SQLite。
