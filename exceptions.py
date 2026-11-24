"""Custom Exception Hierarchy and Error Definitions for AeroLife.

Provides structured, domain-specific, and strictly typed exceptions for atmospheric
telemetry parsing, geocoding failures, Gemini GenAI prompt synthesis, and schema
validation errors across the AeroLife system.
"""

from typing import Any


class AeroLifeBaseException(Exception):
    """Root base exception for all AeroLife system and domain errors.

    Attributes:
        message: Human-readable explanation of the error.
        error_code: Standardized machine-readable error token.
        details: Additional contextual diagnostic telemetry dictionary.
        original_error: Upstream exception that caused this failure, if applicable.
    """

    def __init__(
        self,
        message: str = "An unexpected AeroLife error occurred.",
        error_code: str = "AEROLIFE_GENERAL_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize AeroLifeBaseException.

        Args:
            message: Human-readable explanation of the error.
            error_code: Standardized machine-readable error token.
            details: Optional diagnostic dictionary containing metadata.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message)
        self.message: str = message
        self.error_code: str = error_code
        self.details: dict[str, Any] = details or {}
        self.original_error: Exception | None = original_error

    def __str__(self) -> str:
        """Return standardized string representation of the exception.

        Returns:
            Formatted error string incorporating error code and message.
        """
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            base += f" Details: {self.details}"
        return base


class AirQualityServiceException(AeroLifeBaseException):
    """Base exception for atmospheric telemetry and air quality service failures."""

    def __init__(
        self,
        message: str = "Air quality service operation failed.",
        error_code: str = "AQ_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize AirQualityServiceException.

        Args:
            message: Explanation of atmospheric service failure.
            error_code: Machine-readable telemetry error code.
            details: Optional dictionary containing sensor or station telemetry.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class AtmosphericDataError(AirQualityServiceException):
    """Raised when atmospheric or pollutant sensor readings are invalid or corrupt."""

    def __init__(
        self,
        message: str = "Atmospheric data input is invalid or out of physical bounds.",
        error_code: str = "ATMOSPHERIC_DATA_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize AtmosphericDataError.

        Args:
            message: Explanation of sensor data error.
            error_code: Machine-readable atmospheric data error token.
            details: Optional dictionary containing offending readings.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class CityNotFoundException(AirQualityServiceException):
    """Raised when geocoding fails to resolve a city or locality name."""

    def __init__(
        self,
        city: str,
        message: str | None = None,
        error_code: str = "CITY_NOT_FOUND",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize CityNotFoundException.

        Args:
            city: Unresolvable city or locality query.
            message: Optional override for default error message.
            error_code: Machine-readable geocoding error code.
            details: Optional diagnostic dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        msg: str = (
            message
            or f"Unable to resolve geographic coordinates for locality: '{city}'"
        )
        d: dict[str, Any] = details or {"city": city}
        super().__init__(msg, error_code, d, original_error)
        self.city: str = city


class InvalidAQIValueException(AtmosphericDataError):
    """Raised when an AQI reading violates physical bounds (e.g. negative index)."""

    def __init__(
        self,
        aqi: int,
        message: str | None = None,
        error_code: str = "INVALID_AQI_VALUE",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize InvalidAQIValueException.

        Args:
            aqi: Offending numerical AQI value.
            message: Optional override for default error message.
            error_code: Machine-readable AQI boundary error code.
            details: Optional diagnostic telemetry dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        msg: str = (
            message
            or f"AQI value {aqi} is invalid. AQI must be a non-negative integer."
        )
        d: dict[str, Any] = details or {"aqi": aqi}
        super().__init__(msg, error_code, d, original_error)
        self.aqi: int = aqi


class GeminiEngineException(AeroLifeBaseException):
    """Base exception for Gemini AI Prompt Engine operations."""

    def __init__(
        self,
        message: str = "Gemini AI generation error occurred.",
        error_code: str = "GEMINI_ENGINE_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize GeminiEngineException.

        Args:
            message: Explanation of generative AI engine error.
            error_code: Machine-readable Gemini engine error token.
            details: Optional diagnostic dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class PromptSynthesisError(GeminiEngineException):
    """Raised when prompt construction, model synthesis, or API retry attempts fail."""

    def __init__(
        self,
        message: str = "Failed during prompt synthesis or model communication.",
        error_code: str = "PROMPT_SYNTHESIS_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize PromptSynthesisError.

        Args:
            message: Explanation of prompt synthesis failure.
            error_code: Machine-readable synthesis error token.
            details: Optional dictionary containing input parameters.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class GeminiQuotaExceededException(PromptSynthesisError):
    """Raised when Gemini API rate limit or quota (HTTP 429) is exhausted."""

    def __init__(
        self,
        message: str = "Gemini API rate limit or quota exceeded. Switching to offline engine.",
        error_code: str = "GEMINI_QUOTA_EXCEEDED",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize GeminiQuotaExceededException.

        Args:
            message: Explanation of quota exhaustion.
            error_code: Machine-readable quota error token.
            details: Optional diagnostic dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class GeminiNetworkException(PromptSynthesisError):
    """Raised when network transport or timeout occurs connecting to Gemini API."""

    def __init__(
        self,
        message: str = "Network error communicating with Gemini API. Switching to offline engine.",
        error_code: str = "GEMINI_NETWORK_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize GeminiNetworkException.

        Args:
            message: Explanation of network transport error.
            error_code: Machine-readable network error token.
            details: Optional diagnostic dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class DataValidationException(AeroLifeBaseException):
    """Raised when input parameters or GenAI output fail schema validation."""

    def __init__(
        self,
        message: str = "Data payload failed validation against expected schema.",
        error_code: str = "DATA_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize DataValidationException.

        Args:
            message: Explanation of validation failure.
            error_code: Machine-readable validation error token.
            details: Optional diagnostic dictionary.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


class SchemaValidationError(DataValidationException):
    """Raised specifically when synthesized LLM advisory payload fails Pydantic validation."""

    def __init__(
        self,
        message: str = "Advisory payload does not satisfy Pydantic schema.",
        error_code: str = "SCHEMA_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize SchemaValidationError.

        Args:
            message: Explanation of schema validation mismatch.
            error_code: Machine-readable schema validation error code.
            details: Optional dictionary containing payload and errors.
            original_error: Upstream exception instance triggering this failure.
        """
        super().__init__(message, error_code, details, original_error)


def validate_aqi_bounds(aqi: int, strict: bool = False) -> int:
    """Validate numerical AQI reading boundaries.

    Args:
        aqi: Numerical AQI reading.
        strict: If True, raises InvalidAQIValueException for negative values.

    Returns:
        Clamped (non-negative) or original integer AQI.

    Raises:
        InvalidAQIValueException: If aqi is negative and strict enforcement is enabled.
    """
    if aqi < 0:
        if strict:
            raise InvalidAQIValueException(aqi)
        return 0
    return aqi


def validate_city_name(city: str, strict: bool = False) -> str:
    """Validate and sanitize locality query string.

    Args:
        city: City or locality name string.
        strict: If True, raises CityNotFoundException for empty strings.

    Returns:
        Cleaned, stripped title-cased city name, or default city.

    Raises:
        CityNotFoundException: If city string is empty and strict mode is active.
    """
    cleaned: str = city.strip().title() if city else ""
    if not cleaned:
        if strict:
            raise CityNotFoundException(city)
        return "Delhi"
    return cleaned
