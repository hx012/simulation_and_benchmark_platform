class SimulationTaskError(Exception):
    pass


class TaskNotFoundError(SimulationTaskError):
    pass


class InvalidTaskStateError(SimulationTaskError):
    pass


class UploadSessionError(Exception):
    pass


class UploadSessionNotFoundError(UploadSessionError):
    pass


class InvalidUploadSessionStateError(UploadSessionError):
    pass


class TaskSubmissionError(Exception):
    pass


class TaskQuotaExceededError(TaskSubmissionError):
    pass


class TaskWorkspaceError(Exception):
    pass


class TaskIOError(Exception):
    pass
