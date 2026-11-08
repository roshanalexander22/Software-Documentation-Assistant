"""
FastAPI Web Application and REST API for Software Documentation Assistant.
Provides interactive UI and developer-facing REST endpoints for RAG querying and benchmarking.
"""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from src.config import settings
from src.rag_pipeline import RAGPipeline
from src.evaluator import BenchmarkEvaluator, BENCHMARK_15_QUESTIONS

# Global pipeline instance
pipeline: Optional[RAGPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and pre-warms the RAG pipeline during startup."""
    global pipeline
    print("[INFO] Starting Software Documentation Assistant...")
    pipeline = RAGPipeline()
    pipeline.build_or_load_index(force_reindex=False)
    yield
    print("[INFO] Shutting down Software Documentation Assistant.")


app = FastAPI(
    title="Software Documentation Assistant (RAG)",
    description="Retrieval-Augmented Generation system for developer technical documentation",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development and client integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request and Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, json_schema_extra={"example": "How do I migrate from BaseModel.dict() to Pydantic v2?"})
    top_k: Optional[int] = Field(default=4, ge=1, le=10)
    version_override: Optional[str] = Field(default=None, json_schema_extra={"example": "v2.0"})
    code_only: bool = Field(default=False)


class ReindexRequest(BaseModel):
    force_reindex: bool = Field(default=True)


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Software-Documentation-Assistant",
        "version": "1.0.0",
        "index_ready": pipeline._is_indexed if pipeline else False
    }


@app.get("/api/stats")
async def get_stats():
    """Returns knowledge base indexing and chunk statistics."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline.get_stats()


@app.get("/api/documents")
async def list_documents():
    """Lists all technical documentation files in the knowledge base."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    docs = pipeline.loader.load_all()
    return [
        {
            "doc_id": d.doc_id,
            "title": d.title,
            "version": d.version,
            "framework": d.framework,
            "category": d.category,
            "char_count": d.char_count,
            "tags": d.tags,
            "source_url": d.source_url
        }
        for d in docs
    ]


@app.post("/api/query")
async def query_documentation(req: QueryRequest):
    """Executes grounded RAG query across indexed technical documentation."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    try:
        response = pipeline.query(
            question=req.query,
            top_k=req.top_k,
            version_override=req.version_override,
            code_only=req.code_only
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.post("/api/reindex")
async def reindex_knowledge_base(req: ReindexRequest):
    """Forces re-chunking and re-embedding of documentation files."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    result = pipeline.build_or_load_index(force_reindex=req.force_reindex)
    return result


@app.get("/api/eval")
async def run_evaluation():
    """Executes the standard 15-question benchmark evaluation."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    evaluator = BenchmarkEvaluator(pipeline)
    results = evaluator.run_benchmark(BENCHMARK_15_QUESTIONS)
    return results


# Interactive Modern Developer Web UI
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the interactive single-page application for developers."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Software Documentation Assistant (RAG)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    pre code.hljs { border-radius: 0.5rem; padding: 1rem; font-size: 0.875rem; }
  </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col font-sans">
  <!-- Top Navigation -->
  <header class="bg-slate-800 border-b border-slate-700 py-3 px-6 shadow-md flex justify-between items-center">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow">
        <i class="fa-solid fa-book-bookmark"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white">Software Documentation Assistant</h1>
        <p class="text-xs text-slate-400">Version-Aware RAG Engine with Grounded Citations & Abstention</p>
      </div>
    </div>
    <div class="flex items-center space-x-3 text-xs">
      <span class="px-2.5 py-1 rounded bg-slate-700 text-slate-300 font-mono" id="stats-badge">Indexing...</span>
      <button onclick="runBench()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1.5 rounded transition shadow">
        <i class="fa-solid fa-chart-simple mr-1"></i> Run 15-Q Benchmark
      </button>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-6xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Left Column: Search & Options -->
    <div class="lg:col-span-1 space-y-4">
      <div class="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-sm">
        <h2 class="text-sm font-semibold text-slate-200 mb-3 flex items-center">
          <i class="fa-solid fa-magnifying-glass text-blue-400 mr-2"></i> Query Documentation
        </h2>
        
        <form id="search-form" onsubmit="handleSearch(event)" class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1">Developer Question</label>
            <textarea id="query-input" rows="3" required placeholder="e.g. How do I migrate from BaseModel.dict() to Pydantic v2?"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500 placeholder-slate-500"></textarea>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs">
            <div>
              <label class="block text-slate-400 mb-1 font-medium">Target Version</label>
              <select id="version-filter" class="w-full bg-slate-900 border border-slate-700 rounded-md p-1.5 text-slate-200">
                <option value="">Auto-Detect</option>
                <option value="v2.0">Pydantic v2.0</option>
                <option value="v1.10-legacy">Pydantic v1.10 (Legacy)</option>
                <option value="v0.115">FastAPI v0.115 (Modern)</option>
                <option value="v0.90-legacy">FastAPI v0.90 (Legacy)</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-400 mb-1 font-medium">Top-K Passages</label>
              <select id="top-k" class="w-full bg-slate-900 border border-slate-700 rounded-md p-1.5 text-slate-200">
                <option value="3">3 Chunks</option>
                <option value="4" selected>4 Chunks</option>
                <option value="6">6 Chunks</option>
              </select>
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-1 text-xs text-slate-300">
            <input type="checkbox" id="code-only" class="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0">
            <label for="code-only">Prioritize code examples only</label>
          </div>

          <button type="submit" id="submit-btn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition shadow flex items-center justify-center space-x-2 text-sm">
            <span>Retrieve & Answer</span>
            <i class="fa-solid fa-arrow-right text-xs"></i>
          </button>
        </form>
      </div>

      <!-- Quick Preset Questions -->
      <div class="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-sm text-xs">
        <h3 class="font-semibold text-slate-300 mb-2 flex items-center">
          <i class="fa-solid fa-lightbulb text-yellow-400 mr-2"></i> Sample Benchmark Questions
        </h3>
        <div class="space-y-1.5" id="presets">
          <button onclick="setQuery('How do I migrate from BaseModel.dict() to Pydantic v2 syntax?')" class="w-full text-left p-2 rounded bg-slate-900/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700/50 transition">
            <span class="text-blue-400 font-mono">[V2 Migration]</span> BaseModel.dict() migration
          </button>
          <button onclick="setQuery('What is the recommended modern way to manage startup and shutdown events in FastAPI 0.115?')" class="w-full text-left p-2 rounded bg-slate-900/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700/50 transition">
            <span class="text-emerald-400 font-mono">[FastAPI 0.115]</span> Lifespan Context Manager
          </button>
          <button onclick="setQuery('How do I implement OAuth2 password bearer token authentication with JWT in FastAPI?')" class="w-full text-left p-2 rounded bg-slate-900/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700/50 transition">
            <span class="text-indigo-400 font-mono">[Security]</span> OAuth2 Password Flow + JWT
          </button>
          <button onclick="setQuery('How do I stream generative LLM tokens using StreamingResponse and Server-Sent Events in FastAPI?')" class="w-full text-left p-2 rounded bg-slate-900/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700/50 transition">
            <span class="text-purple-400 font-mono">[Streaming]</span> StreamingResponse & SSE
          </button>
          <button onclick="setQuery('How do I deploy FastAPI directly to an Ethereum smart contract blockchain virtual machine?')" class="w-full text-left p-2 rounded bg-red-950/40 hover:bg-red-900/40 text-red-300 border border-red-800/50 transition">
            <span class="text-red-400 font-mono">[Abstention Test]</span> Out-of-scope blockchain deploy
          </button>
        </div>
      </div>
    </div>

    <!-- Right Column: Results & Evidence -->
    <div class="lg:col-span-2 space-y-4">
      <!-- Loading indicator -->
      <div id="loading" class="hidden bg-slate-800 border border-slate-700 rounded-xl p-8 text-center shadow-sm">
        <i class="fa-solid fa-circle-notch fa-spin text-3xl text-blue-500 mb-3"></i>
        <p class="text-sm font-medium text-slate-300">Executing Hybrid Retrieval & Grounded Generation...</p>
        <p class="text-xs text-slate-500 mt-1">Dense embeddings + BM25 ranking + Citation alignment</p>
      </div>

      <!-- Welcome Banner -->
      <div id="welcome-card" class="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-sm">
        <h2 class="text-base font-semibold text-white mb-2">Welcome to Software Documentation Assistant</h2>
        <p class="text-xs text-slate-300 leading-relaxed">
          This system uses <strong>Retrieval-Augmented Generation (RAG)</strong> to retrieve version-accurate explanations, syntax updates, and intact code blocks from official technical documentation.
        </p>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 text-xs">
          <div class="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
            <div class="text-blue-400 font-bold mb-1"><i class="fa-solid fa-code-compare mr-1"></i> Version-Aware</div>
            <p class="text-slate-400">Distinguishes modern FastAPI 0.115 / Pydantic v2 from legacy patterns.</p>
          </div>
          <div class="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
            <div class="text-emerald-400 font-bold mb-1"><i class="fa-solid fa-shield-halved mr-1"></i> Safe Abstention</div>
            <p class="text-slate-400">Rejects out-of-scope or hallucination queries when evidence is insufficient.</p>
          </div>
          <div class="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
            <div class="text-purple-400 font-bold mb-1"><i class="fa-solid fa-quote-left mr-1"></i> Grounded Citations</div>
            <p class="text-slate-400">Inline citations link each technical statement directly to its origin doc chunk.</p>
          </div>
        </div>
      </div>

      <!-- Answer Card -->
      <div id="answer-card" class="hidden bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-sm space-y-4">
        <!-- Status Header -->
        <div class="flex flex-wrap items-center justify-between pb-3 border-b border-slate-700/80 gap-2">
          <div class="flex items-center space-x-2">
            <span id="abstain-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold"></span>
            <span id="detected-version-badge" class="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300 font-mono"></span>
          </div>
          <div class="flex items-center space-x-3 text-xs text-slate-400 font-mono">
            <span>Score: <strong id="score-val" class="text-slate-200">0.00</strong></span>
            <span>Total: <strong id="latency-val" class="text-slate-200">0ms</strong></span>
          </div>
        </div>

        <!-- Answer Text -->
        <div id="answer-content" class="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed"></div>

        <!-- Citations Box -->
        <div id="citations-box" class="pt-3 border-t border-slate-700 text-xs">
          <span class="font-semibold text-slate-400 block mb-1.5"><i class="fa-solid fa-bookmark text-blue-400 mr-1"></i> Grounded Citations:</span>
          <div id="citations-list" class="flex flex-wrap gap-1.5"></div>
        </div>
      </div>

      <!-- Evidence Drawer -->
      <div id="evidence-card" class="hidden bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-sm">
        <h3 class="text-sm font-semibold text-slate-200 mb-3 flex items-center justify-between">
          <span><i class="fa-solid fa-database text-blue-400 mr-2"></i> Retrieved Evidence Passages (<span id="evidence-count">0</span>)</span>
          <span class="text-xs font-normal text-slate-400">Hybrid Dense + BM25</span>
        </h3>
        <div id="evidence-list" class="space-y-3 text-xs"></div>
      </div>

      <!-- Benchmark Modal / Section -->
      <div id="benchmark-card" class="hidden bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-slate-200 flex items-center">
            <i class="fa-solid fa-clipboard-check text-indigo-400 mr-2"></i> 15-Question Benchmark Results
          </h3>
          <button onclick="document.getElementById('benchmark-card').classList.add('hidden')" class="text-slate-400 hover:text-white text-xs">
            <i class="fa-solid fa-xmark"></i> Close
          </button>
        </div>
        <div id="benchmark-summary" class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs mb-4"></div>
        <div id="benchmark-table" class="overflow-x-auto max-h-96 overflow-y-auto"></div>
      </div>
    </div>
  </main>

  <footer class="bg-slate-800 border-t border-slate-700 py-3 text-center text-xs text-slate-500">
    Software Documentation Assistant &bull; Week 3 Generative AI (RAG) &bull; Verified on Python 3.13
  </footer>

  <script>
    async function initStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stats-badge').innerText = `${data.total_chunks} Chunks (${data.code_chunks} Code)`;
      } catch (e) {
        document.getElementById('stats-badge').innerText = 'Index Active';
      }
    }
    initStats();

    function setQuery(text) {
      document.getElementById('query-input').value = text;
      document.getElementById('search-form').dispatchEvent(new Event('submit'));
    }

    async function handleSearch(e) {
      e.preventDefault();
      const query = document.getElementById('query-input').value.trim();
      const version = document.getElementById('version-filter').value || null;
      const top_k = parseInt(document.getElementById('top-k').value);
      const code_only = document.getElementById('code-only').checked;

      document.getElementById('welcome-card').classList.add('hidden');
      document.getElementById('answer-card').classList.add('hidden');
      document.getElementById('evidence-card').classList.add('hidden');
      document.getElementById('benchmark-card').classList.add('hidden');
      document.getElementById('loading').classList.remove('hidden');

      try {
        const response = await fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, top_k, version_override: version, code_only })
        });
        const data = await response.json();
        renderResult(data);
      } catch (err) {
        alert('Query failed: ' + err.message);
      } finally {
        document.getElementById('loading').classList.add('hidden');
      }
    }

    function renderResult(data) {
      const answerCard = document.getElementById('answer-card');
      const evidenceCard = document.getElementById('evidence-card');
      const abstainBadge = document.getElementById('abstain-badge');

      if (data.is_abstained) {
        abstainBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950 text-red-300 border border-red-800';
        abstainBadge.innerText = 'ABSTENTION: Insufficient Evidence';
      } else {
        abstainBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800';
        abstainBadge.innerText = 'GROUNDED ANSWER';
      }

      document.getElementById('detected-version-badge').innerText = data.detected_version ? `Version: ${data.detected_version}` : 'Version: Auto';
      document.getElementById('score-val').innerText = data.confidence_score.toFixed(3);
      document.getElementById('latency-val').innerText = `${data.latency.total_ms}ms (R: ${data.latency.retrieval_ms}ms, G: ${data.latency.generation_ms}ms)`;

      // Render Markdown
      document.getElementById('answer-content').innerHTML = marked.parse(data.answer);
      document.querySelectorAll('#answer-content pre code').forEach(el => hljs.highlightElement(el));

      // Render Citations
      const citesList = document.getElementById('citations-list');
      citesList.innerHTML = '';
      if (data.citations && data.citations.length > 0) {
        data.citations.forEach(c => {
          const pill = document.createElement('span');
          pill.className = 'px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-mono text-[11px]';
          pill.innerText = c;
          citesList.appendChild(pill);
        });
        document.getElementById('citations-box').classList.remove('hidden');
      } else {
        document.getElementById('citations-box').classList.add('hidden');
      }

      // Render Evidence
      const evList = document.getElementById('evidence-list');
      evList.innerHTML = '';
      document.getElementById('evidence-count').innerText = data.retrieved_chunks.length;
      data.retrieved_chunks.forEach((chunk, i) => {
        const item = document.createElement('div');
        item.className = 'bg-slate-900/80 border border-slate-700/60 rounded-lg p-3 space-y-1.5';
        item.innerHTML = `
          <div class="flex items-center justify-between text-slate-300 font-medium">
            <span>Passage #${i+1}: ${chunk.title} &bull; <em class="text-blue-400 not-italic">${chunk.section}</em></span>
            <span class="font-mono text-emerald-400">Score: ${chunk.score}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono flex items-center space-x-2">
            <span class="bg-slate-800 px-1.5 py-0.5 rounded">ID: ${chunk.chunk_id}</span>
            <span class="bg-slate-800 px-1.5 py-0.5 rounded">Ver: ${chunk.version}</span>
            ${chunk.has_code ? '<span class="bg-indigo-950 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-800">Has Code</span>' : ''}
          </div>
          <div class="text-slate-300 text-xs mt-1 bg-slate-950/60 p-2 rounded border border-slate-800/80 font-mono whitespace-pre-wrap">${escapeHtml(chunk.content_preview)}</div>
        `;
        evList.appendChild(item);
      });

      answerCard.classList.remove('hidden');
      evidenceCard.classList.remove('hidden');
    }

    async function runBench() {
      const benchCard = document.getElementById('benchmark-card');
      const summaryDiv = document.getElementById('benchmark-summary');
      const tableDiv = document.getElementById('benchmark-table');

      benchCard.classList.remove('hidden');
      summaryDiv.innerHTML = '<div class="col-span-4 text-center py-4"><i class="fa-solid fa-spinner fa-spin text-indigo-400 mr-2"></i> Running 15-Question Benchmark...</div>';
      tableDiv.innerHTML = '';

      try {
        const res = await fetch('/api/eval');
        const data = await res.json();
        const s = data.summary;

        summaryDiv.innerHTML = `
          <div class="bg-slate-900 p-2.5 rounded border border-slate-700 text-center">
            <div class="text-slate-400 text-[11px]">Hit Rate@4</div>
            <div class="text-base font-bold text-blue-400">${(s.hit_rate_at_k * 100).toFixed(1)}%</div>
          </div>
          <div class="bg-slate-900 p-2.5 rounded border border-slate-700 text-center">
            <div class="text-slate-400 text-[11px]">Mean Recip. Rank</div>
            <div class="text-base font-bold text-emerald-400">${s.mrr.toFixed(3)}</div>
          </div>
          <div class="bg-slate-900 p-2.5 rounded border border-slate-700 text-center">
            <div class="text-slate-400 text-[11px]">Citation Correctness</div>
            <div class="text-base font-bold text-purple-400">${s.citation_correctness_pct}%</div>
          </div>
          <div class="bg-slate-900 p-2.5 rounded border border-slate-700 text-center">
            <div class="text-slate-400 text-[11px]">Abstention Accuracy</div>
            <div class="text-base font-bold text-amber-400">${s.abstention_accuracy_pct}%</div>
          </div>
        `;

        let rowsHtml = data.results.map(r => `
          <tr class="border-b border-slate-700/60 text-[11px]">
            <td class="p-2 font-mono font-bold">${r.id}</td>
            <td class="p-2">${r.category}</td>
            <td class="p-2 max-w-xs truncate" title="${r.question}">${r.question}</td>
            <td class="p-2 font-mono text-center">${r.confidence_score.toFixed(3)}</td>
            <td class="p-2 text-center">
              <span class="px-1.5 py-0.5 rounded ${r.abstention_status.includes('CORRECT') ? 'bg-emerald-950 text-emerald-300' : 'bg-red-950 text-red-300'} font-semibold">
                ${r.abstention_status}
              </span>
            </td>
            <td class="p-2 font-mono text-right">${r.latency_ms.toFixed(1)}ms</td>
          </tr>
        `).join('');

        tableDiv.innerHTML = `
          <table class="w-full text-left text-slate-300">
            <thead class="bg-slate-900 text-slate-400 uppercase text-[10px] sticky top-0">
              <tr>
                <th class="p-2">#</th>
                <th class="p-2">Category</th>
                <th class="p-2">Question</th>
                <th class="p-2 text-center">Top Score</th>
                <th class="p-2 text-center">Status</th>
                <th class="p-2 text-right">Latency</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        `;
      } catch (err) {
        summaryDiv.innerHTML = `<div class="col-span-4 text-red-400">Error: ${err.message}</div>`;
      }
    }

    function escapeHtml(text) {
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
