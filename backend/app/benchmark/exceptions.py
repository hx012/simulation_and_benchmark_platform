class BenchmarkError(RuntimeError):
    """Base error for Benchmark backend operations."""


class BenchmarkNotConfiguredError(BenchmarkError):
    """Raised when the aibench registry location is not configured."""


class BenchmarkRegistryNotFoundError(BenchmarkError):
    """Raised when a configured registry file cannot be found."""


class BenchmarkRegistryFormatError(BenchmarkError):
    """Raised when registry JSON does not match the expected structure."""


class BenchmarkChipNotFoundError(BenchmarkError):
    """Raised when a vendor/chip pair is not registered."""


class BenchmarkDefinitionNotFoundError(BenchmarkError):
    """Raised when a benchmark is not registered for a chip."""
