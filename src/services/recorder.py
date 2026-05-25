from src.config import Config
from src.repositories.send_record_repo import SendRecordRepository
from src.schemas.marketing import MarketingWorkflowState


class MarketingRecorder:
    """营销发送记录服务。"""

    def __init__(
        self,
        repo: SendRecordRepository | None = None,
        config: Config | None = None,
    ):
        self.repo = repo or SendRecordRepository(config=config)

    def record(self, state: MarketingWorkflowState) -> str:
        return self.repo.save(state)
