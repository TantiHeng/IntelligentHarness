"""系统错误分类：区分可重试推理故障与不可重试程序或配置故障。"""


class HarnessSystemError(RuntimeError):
    """Base class for system failures that must not become business rejections."""


class RetryableInferenceError(HarnessSystemError):
    """Inference failed because of a transient upstream or network condition."""


class NonRetryableInferenceError(HarnessSystemError):
    """Inference failed because retrying the same request is not expected to help."""


_RETRYABLE_EXCEPTION_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "ConnectError",
    "ConnectTimeout",
    "PoolTimeout",
    "RateLimitError",
    "ReadTimeout",
    "TimeoutException",
}


def classify_inference_error(error: Exception) -> HarnessSystemError:
    """Normalize adapter exceptions without coupling the workflow to an SDK."""
    if isinstance(error, HarnessSystemError):
        return error
    if isinstance(error, (ConnectionError, TimeoutError)):
        return RetryableInferenceError(str(error))
    if type(error).__name__ in _RETRYABLE_EXCEPTION_NAMES:
        return RetryableInferenceError(str(error))
    return NonRetryableInferenceError(str(error))
