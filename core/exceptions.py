class SVOSException(Exception):
    """Base SVOS exception with optional machine-readable code."""

    def __init__(self, message: str, code: str = "SVOS_ERROR"):
        super().__init__(message)
        self.code = code


class ConfigError(SVOSException):
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")


class RegistryError(SVOSException):
    def __init__(self, message: str = "Registry operation failed"):
        super().__init__(message, code="REGISTRY_ERROR")


class PortReservationError(SVOSException):
    def __init__(self, message: str = "Port reservation failed"):
        super().__init__(message, code="PORT_RESERVATION_ERROR")


class ConstitutionViolation(SVOSException):
    def __init__(self, message: str = "Decision violates business constitution"):
        super().__init__(message, code="CONSTITUTION_VIOLATION")


class ProviderError(SVOSException):
    def __init__(self, message: str = "LLM provider request failed"):
        super().__init__(message, code="PROVIDER_ERROR")


class DatabaseError(SVOSException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, code="DATABASE_ERROR")


class MCPError(SVOSException):
    def __init__(self, message: str = "MCP operation failed"):
        super().__init__(message, code="MCP_ERROR")
