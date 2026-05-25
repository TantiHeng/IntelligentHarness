# AgentWorkflow-IntelligentMarketingAssistant_AutoSend-
用 LangGraph 实现了一个针对高副作用业务场景的受控 Agent 工作流，重点解决结构化生成、合规审核回路、失败留痕、组件可替换和后续恢复执行的演进边界。这是一个基于 LangGraph 和 LangChain 的受控营销内容生成工作流 Demo。它面向 B2B 营销场景，输入产品信息和客户画像后，由大模型生成营销文案，再经过规则审核和 LLM 语义审核；如果审核不通过，工作流会根据审核建议自动改写，审核通过后进入 mock 发送节点，并将运行结果记录到 SQLite。
使用 Pydantic 定义输入、内容、审核结果、发送结果和工作流状态，确保节点之间传递的是结构化数据。
使用 LangGraph 表达生成、审核、改写、发送、失败记录等状态流转，而不是把所有逻辑堆在一个函数里。
将 prompt 独立管理，并通过本地 JSON parser 和 Pydantic 校验模型输出，避免依赖部分兼容模型并不稳定支持的 provider-native structured output。
将配置集中管理，包括模型参数、重试次数和数据库路径。
支持对 generator、reviewer、sender、recorder 进行依赖注入，测试时不需要访问真实模型或写真实业务依赖。
为每次运行生成 run_id 和 thread_id，前者用于业务追踪，后者为未来接入 checkpoint 与 interrupt/resume 预留。
当前发送模块明确采用 mock 实现，因为这个版本的重点是验证工作流设计、风险控制、错误分支与可测试性，而不是接入真实外部副作用。
