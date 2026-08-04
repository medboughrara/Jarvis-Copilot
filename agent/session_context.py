"""
Session Context Management for Jarvis PCB Copilot.
Provides isolated session-bound model caches and engine instances (RAG, OmniParser, Unlimited-OCR)
per JarvisAgent instance or MCP session, avoiding process-wide mutable global state leaks.
"""

from typing import Dict, Any, Optional
import config

logger = config.get_logger(__name__)


class JarvisSessionContext:
    """Session container isolating schematic models, RAG stores, and OCR engines per agent/MCP session."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "default_session"
        self.schematic_cache: Dict[str, Any] = {}  # sha256_hash -> SchematicModel
        self._rag_engine: Optional[Any] = None
        self._omniparser_engine: Optional[Any] = None
        self._unlimited_ocr_engine: Optional[Any] = None

    def get_schematic_model(self, file_hash: str) -> Optional[Any]:
        """Retrieves cached SchematicModel by SHA-256 hash if present in session."""
        return self.schematic_cache.get(file_hash)

    def cache_schematic_model(self, file_hash: str, model: Any):
        """Caches a parsed SchematicModel keyed by SHA-256 hash for the duration of the session."""
        self.schematic_cache[file_hash] = model

    def get_rag_engine(self) -> Any:
        """Lazy-loads and returns session-scoped DatasheetRAG instance."""
        if self._rag_engine is None:
            from tools.datasheet_rag_tool import DatasheetRAG
            logger.info(f"[SessionContext:{self.session_id}] Initializing session-scoped DatasheetRAG engine...")
            self._rag_engine = DatasheetRAG()
        return self._rag_engine

    def get_omniparser_engine(self) -> Any:
        """Lazy-loads and returns session-scoped OmniParserTool instance."""
        if self._omniparser_engine is None:
            from tools.omniparser_tool import OmniParserTool
            logger.info(f"[SessionContext:{self.session_id}] Initializing session-scoped OmniParser engine...")
            self._omniparser_engine = OmniParserTool()
        return self._omniparser_engine

    def get_unlimited_ocr_engine(self) -> Any:
        """Lazy-loads and returns session-scoped UnlimitedOCRTool instance."""
        if self._unlimited_ocr_engine is None:
            from tools.unlimited_ocr_tool import UnlimitedOCRTool
            logger.info(f"[SessionContext:{self.session_id}] Initializing session-scoped Unlimited-OCR engine...")
            self._unlimited_ocr_engine = UnlimitedOCRTool()
        return self._unlimited_ocr_engine
