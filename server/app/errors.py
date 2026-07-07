class GuideServerError(Exception):
    """后端可预期的业务错误。"""


class DataValidationError(GuideServerError):
    """数据文件内容不合法。"""


class LocationNotFoundError(GuideServerError):
    """地点不存在。"""


class RouteNotFoundError(GuideServerError):
    """两地点之间不存在满足条件的路线。"""


class VisualLocalizationError(GuideServerError):
    """视觉定位无法完成。"""


class VlmNotConfiguredError(VisualLocalizationError):
    """尚未配置 VLM 服务。"""


class VlmResponseError(VisualLocalizationError):
    """VLM 请求失败或响应格式错误。"""
