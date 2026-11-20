from pydantic import BaseModel


class ResponseOperationResult(BaseModel):
    message: str = ""
    status: str

class ResponseOperationSuccess(ResponseOperationResult):
    message: str = "Operation completed successfully"
    status: str = "success"

class ResponseOperationFailure(ResponseOperationResult):
    message: str = "Operation failed"
    status: str = "failure"