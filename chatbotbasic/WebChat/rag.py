# rag.py
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Iterable
from urllib.parse import urlparse

from git import Repo

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser

_CACHE_DIR = Path(".rag_cache")
_CACHE_DIR.mkdir(exist_ok=True)
_VS_CACHE: Dict[str, FAISS] = {}
_VS_CACHE_MERGED: Dict[tuple, FAISS] = {}

_SUFFIXES = [
    ".py", ".md", ".txt", ".ts", ".tsx", ".js",
    ".java", ".go", ".rs", ".cpp", ".c", ".cs",
    ".json", ".yml", ".yaml"
]

def _repo_key(repo_url: str, commit: str) -> str:
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")
    owner = parts[0] if len(parts) > 0 else "owner"
    repo = parts[1] if len(parts) > 1 else "repo"
    return f"{owner}__{repo}__{commit}"

def _clone_repo(repo_url: str) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="repo_"))
    Repo.clone_from(repo_url, tmpdir)
    return tmpdir

def _get_head_commit(repo_dir: Path) -> str:
    try:
        repo = Repo(repo_dir)
        return repo.head.commit.hexsha[:10]
    except Exception:
        return "unknown"

def _load_repo_docs(repo_dir: Path) -> List[Document]:
    loader = GenericLoader.from_filesystem(
        str(repo_dir),
        glob="**/*",
        suffixes=_SUFFIXES,
        parser=LanguageParser(language=None, parser_threshold=50000), 
        show_progress=True,
        exclude=[
            ".git", "**/.git/**", "**/node_modules/**", "**/.venv/**",
            "**/dist/**", "**/build/**", "**/.next/**", "**/.cache/**"
        ],
    )
    docs = loader.load()
    for d in docs:
        try:
            rel = Path(d.metadata.get("source", "")).relative_to(repo_dir)
            d.metadata["repo_path"] = rel.as_posix()
        except Exception:
            pass
    return docs

def _chunk_docs(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\nclass ", "\nfunction ", "\ndef ", "\n# ", "\n", " ", ""],
    )
    return splitter.split_documents(docs)

def _save_vs(vs: FAISS, cache_key: str):
    vs_dir = _CACHE_DIR / cache_key
    vs_dir.mkdir(exist_ok=True, parents=True)
    vs.save_local(str(vs_dir))

def _load_vs(embeddings: OpenAIEmbeddings, cache_key: str) -> Optional[FAISS]:
    vs_dir = _CACHE_DIR / cache_key
    if vs_dir.exists():
        try:
            return FAISS.load_local(str(vs_dir), embeddings, allow_dangerous_deserialization=True)
        except Exception:
            return None
    return None

def _get_embeddings():
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("Set OPENAI_API_KEY for embeddings and LLM.")
    return OpenAIEmbeddings(model="text-embedding-3-small")

def _vectorstore_for_repo(repo_url: str) -> FAISS:
    """
    Build or load a FAISS vectorstore for a single repo.
    Cached in-memory and on-disk per commit.
    """
    if repo_url in _VS_CACHE:
        return _VS_CACHE[repo_url]

    embeddings = _get_embeddings()

    repo_dir = _clone_repo(repo_url)
    head = _get_head_commit(repo_dir)
    cache_key = _repo_key(repo_url, head)

    cached_vs = _load_vs(embeddings, cache_key)
    if cached_vs:
        _VS_CACHE[repo_url] = cached_vs
        return cached_vs

    docs = _load_repo_docs(repo_dir)
    chunks = _chunk_docs(docs)
    vs = FAISS.from_documents(chunks, embeddings)
    _save_vs(vs, cache_key)
    _VS_CACHE[repo_url] = vs
    return vs

def build_retriever_for_repo(repo_url: str):
    vs = _vectorstore_for_repo(repo_url)
    return vs.as_retriever(search_kwargs={"k": 5})

def build_retriever_for_repos(repo_urls: Iterable[str]):
    """
    Merge FAISS indexes from multiple repos into a single retriever.
    Uses the same embedding model for consistency.
    """
    repo_urls = tuple(sorted(set(u for u in repo_urls if u)))  # canonical key
    if not repo_urls:
        raise ValueError("No repositories provided.")

    if repo_urls in _VS_CACHE_MERGED:
        return _VS_CACHE_MERGED[repo_urls].as_retriever(search_kwargs={"k": 6})

    # Build / load individual vectorstores
    vs_list: List[FAISS] = [_vectorstore_for_repo(u) for u in repo_urls]
    base = vs_list[0]
    for other in vs_list[1:]:
        base.merge_from(other)

    _VS_CACHE_MERGED[repo_urls] = base
    return base.as_retriever(search_kwargs={"k": 6})

def rag_answer(repo_url: str, question: str, chat_history=None) -> str:
    retriever = build_retriever_for_repo(repo_url)
    return _rag_ask_with_retriever(retriever, question, repo_hint=repo_url)

def rag_answer_multi(repo_urls: List[str], question: str, chat_history=None) -> str:
    retriever = build_retriever_for_repos(repo_urls)
    return _rag_ask_with_retriever(retriever, question, repo_hint=", ".join(repo_urls))

def _rag_ask_with_retriever(retriever, question: str, repo_hint: str = "") -> str:
    relevant_docs = retriever.get_relevant_documents(question)

    system = (
        "You are a helpful software assistant. Rely on the provided repository context. "
        "Cite filenames/paths from metadata when helpful. If unsure, say you’re unsure."
    )

    context_blocks = []
    for d in relevant_docs:
        path = d.metadata.get("repo_path") or d.metadata.get("source", "")
        context_blocks.append(f"[{path}]\n{d.page_content}")

    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant repo context found."

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "Repos: {repo_hint}\n\nQuestion: {question}\n\nContext:\n{context}")
    ])

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    resp = (prompt | llm).invoke({"repo_hint": repo_hint, "question": question, "context": context})
    return resp.content
