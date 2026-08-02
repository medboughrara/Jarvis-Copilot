"""
Datasheet RAG Tool for Jarvis PCB Copilot.
Enables Retrieval-Augmented Generation over arbitrary component PDFs using CPU-bound embeddings.
"""

import os
import glob
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


class DatasheetRAG:
    """CPU-friendly RAG engine for parsing and querying local PDF datasheets."""

    def __init__(self, data_dir: str = "datasheets", persist_dir: str = "scratch/chromadb"):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        
        if not RAG_AVAILABLE:
            return
            
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.persist_dir, exist_ok=True)

        logger.info(f"Initializing CPU Embedding Model (all-MiniLM-L6-v2) for RAG...")
        # Use a very small model explicitly set to CPU to preserve VRAM for Ollama
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

    def ingest_new_datasheets(self):
        """Finds PDFs in the datasheets directory and adds them to the vector store."""
        if not RAG_AVAILABLE:
            return "RAG dependencies not installed."
            
        pdf_files = glob.glob(os.path.join(self.data_dir, "*.pdf"))
        if not pdf_files:
            return f"No PDF datasheets found in '{self.data_dir}'."

        # Simplistic approach: if we have more than 0 files, we clear and re-ingest for demonstration.
        # In production, check for existing document IDs.
        logger.info(f"Found {len(pdf_files)} PDFs in '{self.data_dir}'. Ingesting...")
        
        all_splits = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        for pdf in pdf_files:
            logger.info(f"Loading {os.path.basename(pdf)}...")
            loader = PyPDFLoader(pdf)
            docs = loader.load()
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)

        if all_splits:
            self.vector_store.add_documents(documents=all_splits)
            return f"Successfully ingested {len(pdf_files)} datasheets into local Chroma vector store."
        return "No text could be extracted from the PDFs."

    def query_datasheets(self, query: str) -> str:
        """Performs similarity search on the local datasheet vector store."""
        if not RAG_AVAILABLE:
            return "RAG capability is offline due to missing dependencies. Use web search instead."

        logger.info(f"Executing RAG query: '{query}'")
        
        # Ensure we have docs; if not, try to ingest
        if self.vector_store._collection.count() == 0:
            ingest_msg = self.ingest_new_datasheets()
            if "No PDF datasheets found" in ingest_msg:
                return ingest_msg

        results = self.vector_store.similarity_search(query, k=3)
        if not results:
            return f"No relevant information found in local datasheets for '{query}'."

        summary = [f"[Local Datasheet Search Results for '{query}']:"]
        for i, res in enumerate(results):
            source = os.path.basename(res.metadata.get('source', 'Unknown'))
            page = res.metadata.get('page', '?')
            summary.append(f"• Source: {source} (Page {page})\n  Excerpt: {res.page_content[:250]}...")
            
        return "\n\n".join(summary)


# ---------------------------------------------------------------------------
# LangChain Tool Function
# ---------------------------------------------------------------------------

@tool
def query_local_datasheets(query: str) -> str:
    """
    Searches through locally downloaded PDF datasheets (in the 'datasheets' folder) using RAG.
    Use this tool when the user explicitly asks to query a local PDF or document.
    Args:
        query: The question or search term (e.g. 'What is the maximum operating temperature of the IC?').
    """
    rag = DatasheetRAG()
    return rag.query_datasheets(query)
