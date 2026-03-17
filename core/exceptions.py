class SVOSException(Exception):
    """Base SVOS exception."""


class RegistryError(SVOSException):
    """Registry operation failed."""


class PortReservationError(SVOSException):
    """Port reservation failed."""


class ConstitutionViolation(SVOSException):
    """Decision violates business constitution."""
