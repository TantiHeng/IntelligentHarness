from typing import Optional

from langgraph.graph import END, START, StateGraph

from src.config import Config
from src.exceptions import (
    MarketingContentMissingError,
    MarketingReviewRejectedError,
    MarketingSendFailedError,
)
from src.llm import LLMClient
from src.logger import logger
from src.schemas.marketing import MarketingWorkflowState
from src.services.generator import MarketingGenerator
from src.services.recorder import MarketingRecorder
from src.services.reviewer import MarketingReviewer
from src.services.sender import MarketingSender


class MarketingWorkflow:
    """
    营销内容自动化工作流。

    run_id:
        单次业务运行 ID，用于日志、数据库记录和后续审计。

    thread_id:
        LangGraph 线程 ID，用于后续接入 checkpointer / interrupt / resume。
        当前阶段先写入 config，不启用 checkpointer。
    """

    def __init__(
        self,
        generator: Optional[MarketingGenerator] = None,
        reviewer: Optional[MarketingReviewer] = None,
        sender: Optional[MarketingSender] = None,
        recorder: Optional[MarketingRecorder] = None,
        llm_client: Optional[LLMClient] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.config = config or Config()
        self.max_retries = self.config.WORKFLOW_MAX_RETRIES

        if generator is None or reviewer is None:
            resolved_llm_client = llm_client or LLMClient(config=self.config)
        else:
            resolved_llm_client = llm_client

        self.generator = generator or MarketingGenerator(resolved_llm_client)
        self.reviewer = reviewer or MarketingReviewer(resolved_llm_client)
        self.sender = sender or MarketingSender()
        self.recorder = recorder or MarketingRecorder(config=self.config)

        self.app = self._build_graph()

    def _generate_node(self, state: MarketingWorkflowState) -> dict:
        logger.info(
            "开始生成营销内容: run_id=%s, thread_id=%s",
            state.run_id,
            state.thread_id,
        )

        content = self.generator.generate(state.input)

        logger.info(
            "营销内容生成完成: run_id=%s, title=%s",
            state.run_id,
            content.title,
        )

        return {"content": content}

    def _review_node(self, state: MarketingWorkflowState) -> dict:
        logger.info("开始审核营销内容: run_id=%s", state.run_id)

        if state.content is None:
            logger.error("审核失败: run_id=%s, content 为空", state.run_id)
            raise MarketingContentMissingError("content 为空，无法审核。")

        review = self.reviewer.review(state.content)

        logger.info(
            "审核完成: run_id=%s, approved=%s, score=%s, reasons=%s, suggestions=%s",
            state.run_id,
            review.approved,
            review.score,
            review.reasons,
            review.revision_suggestions,
        )

        return {"review": review}

    def _revise_node(self, state: MarketingWorkflowState) -> dict:
        logger.info(
            "审核未通过，准备基于审核建议改写: run_id=%s, retry_count=%s",
            state.run_id,
            state.retry_count,
        )

        if state.content is None:
            raise MarketingContentMissingError("content 为空，无法改写。")

        if state.review is None:
            raise MarketingReviewRejectedError("review 为空，无法根据审核意见改写。")

        if state.retry_count >= self.max_retries:
            logger.error(
                "超过最大重试次数，终止流程: run_id=%s, retry_count=%s, max_retries=%s, review=%s",
                state.run_id,
                state.retry_count,
                self.max_retries,
                state.review,
            )
            raise MarketingReviewRejectedError("营销内容未通过审核，且已超过最大重试次数。")

        revised_content = self.generator.revise(
            marketing_input=state.input,
            content=state.content,
            review=state.review,
        )

        logger.info(
            "营销内容改写完成: run_id=%s, retry_count=%s, title=%s",
            state.run_id,
            state.retry_count + 1,
            revised_content.title,
        )

        return {"content": revised_content, "retry_count": state.retry_count + 1}

    def _reject_node(self, state: MarketingWorkflowState) -> dict:
        logger.error(
            "营销内容审核未通过: run_id=%s, retry_count=%s, review=%s",
            state.run_id,
            state.retry_count,
            state.review,
        )

        try:
            record_id = self.recorder.record(state)
            logger.info("审核失败结果已记录: run_id=%s, record_id=%s", state.run_id, record_id)
        except Exception as exc:
            logger.exception("审核失败结果记录失败: run_id=%s, error=%s", state.run_id, exc)

        reasons = state.review.reasons if state.review else ["无审核结果"]
        raise MarketingReviewRejectedError(f"营销内容未通过审核: {reasons}")

    def _send_node(self, state: MarketingWorkflowState) -> dict:
        logger.info("开始发送营销内容: run_id=%s", state.run_id)

        if state.content is None:
            logger.error("发送失败: run_id=%s, content 为空", state.run_id)
            raise MarketingContentMissingError("content 为空，无法发送。")

        send_result = self.sender.send(state.input, state.content)

        logger.info(
            "发送完成: run_id=%s, success=%s, provider_message_id=%s, error=%s",
            state.run_id,
            send_result.success,
            send_result.provider_message_id,
            send_result.error,
        )

        if not send_result.success:
            logger.error("mock 发送失败路径触发: run_id=%s, error=%s", state.run_id, send_result.error)

        return {"send_result": send_result}

    def _send_failed_node(self, state: MarketingWorkflowState) -> dict:
        logger.error(
            "发送失败，准备记录失败结果: run_id=%s, send_result=%s",
            state.run_id,
            state.send_result,
        )

        record_id = self.recorder.record(state)

        logger.info("发送失败结果已记录: run_id=%s, record_id=%s", state.run_id, record_id)

        error = state.send_result.error if state.send_result and state.send_result.error else "发送失败。"
        raise MarketingSendFailedError(error)

    def _record_node(self, state: MarketingWorkflowState) -> dict:
        logger.info("开始记录发送结果: run_id=%s", state.run_id)

        record_id = self.recorder.record(state)

        logger.info("发送结果记录完成: run_id=%s, record_id=%s", state.run_id, record_id)

        return {"record_id": record_id}

    def _route_after_review(self, state: MarketingWorkflowState) -> str:
        if state.review is None:
            logger.error("审核节点未产生 review，进入 reject: run_id=%s", state.run_id)
            return "reject"

        if state.review.approved:
            return "send"

        if state.retry_count < self.max_retries:
            return "revise"

        return "reject"

    def _route_after_send(self, state: MarketingWorkflowState) -> str:
        if state.send_result is None:
            return "send_failed"

        if state.send_result.success:
            return "record"

        return "send_failed"

    def _build_graph(self):
        graph = StateGraph(MarketingWorkflowState)

        graph.add_node("generate", self._generate_node)
        graph.add_node("review", self._review_node)
        graph.add_node("revise", self._revise_node)
        graph.add_node("reject", self._reject_node)
        graph.add_node("send", self._send_node)
        graph.add_node("send_failed", self._send_failed_node)
        graph.add_node("record", self._record_node)

        graph.add_edge(START, "generate")
        graph.add_edge("generate", "review")

        graph.add_conditional_edges(
            "review",
            self._route_after_review,
            {"send": "send", "revise": "revise", "reject": "reject"},
        )

        graph.add_edge("revise", "review")

        graph.add_conditional_edges(
            "send",
            self._route_after_send,
            {"record": "record", "send_failed": "send_failed"},
        )

        graph.add_edge("record", END)

        return graph.compile()

    def invoke(self, state: MarketingWorkflowState) -> MarketingWorkflowState:
        runtime_config = {"configurable": {"thread_id": state.thread_id}}
        result = self.app.invoke(state, config=runtime_config)
        return MarketingWorkflowState.model_validate(result)
