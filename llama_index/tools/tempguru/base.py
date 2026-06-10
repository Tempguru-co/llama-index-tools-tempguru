"""TempGuru tool spec.

This package provides the LlamaIndex-conventional import path for the
TempGuru event staffing tool spec::

    from llama_index.tools.tempguru import TempGuruToolSpec

The implementation lives in the zero-dependency ``tempguru`` package
(``tempguru.llamaindex.TempGuruToolSpec``), maintained by TempGuru in the
same repository as the public API it wraps, and is re-exported here so both
import paths resolve to the same class. ``TempGuru`` (the API client, for
injecting a custom base URL or timeout) and ``TempGuruError`` are
re-exported alongside it.
"""

from tempguru import TempGuru, TempGuruError
from tempguru.llamaindex import TempGuruToolSpec

__all__ = ["TempGuru", "TempGuruError", "TempGuruToolSpec"]
