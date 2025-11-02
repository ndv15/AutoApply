"""Provider registry exposing the current provider bundle.

This module reads configuration from :mod:`autoapply.config.env` and
returns a bundle of providers for research, generation and reranking.
Real providers can be added here keyed off ``ENV.PROVIDER_PRIMARY``.
"""

from autoapply.config.env import ENV
from autoapply.providers.base import ProviderBundle
from autoapply.providers.mock import MockResearch, MockRerank, MockGenerator


def get_providers() -> ProviderBundle:
    """Return a provider bundle based on configuration.

    For now only a mock provider is available.  In the future this
    function could read ``ENV.PROVIDER_PRIMARY`` and instantiate a
    provider bundle accordingly.
    """
    # When adding real providers, use ENV.PROVIDER_PRIMARY to select.
    return {
        "research": MockResearch(),
        "generator": MockGenerator(),
        "rerank": MockRerank(),
    }