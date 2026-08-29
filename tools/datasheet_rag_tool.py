"""
Datasheet RAG Tool for Jarvis PCB Copilot.
Enables Retrieval-Augmented Generation over arbitrary component PDFs using CPU-bound embeddings.
"""

import os
import glob
from typing import Optional, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG dependencies missing: {e}")
    RAG_AVAILABLE = False


class NvidiaNemotronEmbeddings:
    """LangChain-compatible wrapper for NVIDIA Nemotron 3 Embed 1B."""
    def __init__(self):
        from tools.nvidia_nim_tool import NvidiaNIMClient
        self.client = NvidiaNIMClient()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.client.get_embeddings(texts)

    def embed_query(self, text: str) -> list[float]:
        res = self.client.get_embeddings([text])
        return res[0] if res else []


class DatasheetRAG:
    """CPU & Cloud RAG engine for parsing and querying local PDF datasheets with incremental ingestion."""

    def __init__(self, data_dir: str = "datasheets", persist_dir: str = "scratch/chromadb"):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.ingested_files = set()
        
        if not RAG_AVAILABLE:
            return
            
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.persist_dir, exist_ok=True)

        if getattr(config, "NVIDIA_NEMOTRON_EMBED_KEY", ""):
            logger.info("Initializing NVIDIA Nemotron 3 Embed 1B Cloud Embedding Model for RAG...")
            self.embeddings = NvidiaNemotronEmbeddings()
        else:
            logger.info("Initializing CPU Embedding Model (all-MiniLM-L6-v2) for RAG...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
        
        self.vector_store = Chroma(
            collection_name="datasheets",
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir
        )

    def ingest_new_datasheets(self) -> str:
        """Finds new or uningested PDFs in the datasheets directory and incrementally adds them to the vector store."""
        if not RAG_AVAILABLE:
            return "RAG dependencies not installed."
            
        pdf_files = glob.glob(os.path.join(self.data_dir, "*.pdf"))
        if not pdf_files:
            return f"No PDF datasheets found in '{self.data_dir}'."

        # Filter out already ingested files in this session
        new_pdf_files = [f for f in pdf_files if os.path.abspath(f) not in self.ingested_files]
        if not new_pdf_files and self.vector_store._collection.count() > 0:
            return f"All {len(pdf_files)} PDF datasheets are already ingested."

        logger.info(f"Found {len(new_pdf_files)} new PDFs to ingest in '{self.data_dir}'...")
        
        all_splits = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        for pdf in new_pdf_files:
            logger.info(f"Loading {os.path.basename(pdf)}...")
            try:
                loader = PyPDFLoader(pdf)
                docs = loader.load()
                splits = text_splitter.split_documents(docs)
                all_splits.extend(splits)
                self.ingested_files.add(os.path.abspath(pdf))
            except Exception as e:
                logger.warning(f"Could not load PDF '{pdf}': {e}")

        if all_splits:
            self.vector_store.add_documents(documents=all_splits)
            return f"Successfully ingested {len(new_pdf_files)} new datasheets into Chroma vector store."
        return "No new text could be extracted from the PDFs."

    def query_datasheets(self, query: str) -> str:
        """Performs similarity search on the local datasheet vector store."""
        if not RAG_AVAILABLE:
            return "RAG capability is offline due to missing dependencies. Use web search instead."

        logger.info(f"Executing RAG query: '{query}'")
        
        # Check for and incrementally ingest any newly added PDF files
        self.ingest_new_datasheets()

        if self.vector_store._collection.count() == 0:
            return f"No PDF datasheets found in '{self.data_dir}'."

        results = self.vector_store.similarity_search(query, k=3)
        if not results:
            return f"No relevant information found in local datasheets for '{query}'."

        from agent.security import agentshield
        summary = [f"[Local Datasheet Search Results for '{query}']:"]
        for i, res in enumerate(results):
            source = os.path.basename(res.metadata.get('source', 'Unknown'))
            page = res.metadata.get('page', '?')
            clean_content = agentshield.sanitize_untrusted_content(res.page_content[:250])
            summary.append(f"• Source: {source} (Page {page})\n  Excerpt: {clean_content}...")
            
        return "\n\n".join(summary)


# ---------------------------------------------------------------------------
# Session-Scoped RAG Instance Helper & LangChain Tool
# ---------------------------------------------------------------------------

def get_datasheet_rag(session_context: Optional[Any] = None) -> DatasheetRAG:
    """Returns session-scoped DatasheetRAG instance or fresh instance."""
    if session_context and hasattr(session_context, 'get_rag_engine'):
        return session_context.get_rag_engine()
    return DatasheetRAG()


@tool
def query_local_datasheets(query: str) -> dict:
    """
    Queries local PDF datasheets in datasheets/ directory using semantic vector search.
    """
    try:
        rag = get_datasheet_rag()
        res_text = rag.query_datasheets(query)
        summary_str = f"Local Datasheet RAG Query for '{query}': {res_text[:120]}..."
        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "query": query,
                "rag_result": res_text
            }
        }
    except Exception as e:
        logger.error(f"[query_local_datasheets Error] {e}")
        return {
            "status": "error",
            "summary": f"Error querying local datasheets: {e}",
            "data": {"error": str(e)}
        }
