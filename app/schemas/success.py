from pydantic import BaseModel


class OperationResult(BaseModel):
    message: str = ""
    status: str

class OperationSuccess(OperationResult):
    message: str = "Operation completed successfully"
    status: str = "success"

class OperationFailure(OperationResult):
    message: str = "Operation failed"
    status: str = "failure"