from app.port.restful.response import ApiResponse


def health():
    return ApiResponse.success(None)
