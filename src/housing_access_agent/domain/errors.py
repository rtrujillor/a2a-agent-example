"""Workflow errors that the A2A layer maps to a failed task."""


class ClassificationError(Exception):
    """The model's output could not be validated after the bounded retries."""


class ModelUnavailableError(Exception):
    """The language model could not be reached or returned a provider error."""
