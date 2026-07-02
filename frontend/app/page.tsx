"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { queryDocs, type QueryResponse } from "@/lib/api";

const LIBRARIES = [
  {
    id: "nextjs",
    label: "Next.js",
    activeClass: "bg-zinc-900 text-white",
    gradient: "from-zinc-700 to-zinc-500",
    examples: [
      "How do server actions work?",
      "What is the App Router?",
      "How do I optimise images?",
    ],
  },
  {
    id: "langchain",
    label: "LangChain",
    activeClass: "bg-green-600 text-white",
    gradient: "from-green-600 to-emerald-500",
    examples: [
      "How do I build a RAG chain?",
      "What are LCEL runnables?",
      "How do I add conversation memory?",
    ],
  },
  {
    id: "llamaindex",
    label: "LlamaIndex",
    activeClass: "bg-violet-600 text-white",
    gradient: "from-violet-600 to-purple-500",
    examples: [
      "How do I create a VectorStoreIndex?",
      "What is a query engine?",
      "How do I use sub-question queries?",
    ],
  },
  {
    id: "haystack",
    label: "Haystack",
    activeClass: "bg-orange-500 text-white",
    gradient: "from-orange-500 to-amber-400",
    examples: [
      "How do I build a pipeline?",
      "How does the DocumentStore work?",
      "What are Haystack components?",
    ],
  },
];

const PIPELINE_STEPS = [
  { label: "Embedding question",      ms: 2000 },
  { label: "Searching documentation", ms: 1500 },
  { label: "Reranking results",       ms: 3500 },
  { label: "Generating answer",       ms: Infinity },
];

function ProgressLoader() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    let current = 0;
    const advance = () => {
      current += 1;
      if (current < PIPELINE_STEPS.length) {
        setStep(current);
        setTimeout(advance, PIPELINE_STEPS[current].ms);
      }
    };
    const timer = setTimeout(advance, PIPELINE_STEPS[0].ms);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col">
      {PIPELINE_STEPS.map((s, i) => {
        const done   = i < step;
        const active = i === step;
        const last   = i === PIPELINE_STEPS.length - 1;
        return (
          <div key={i} className="flex items-stretch gap-4">
            {/* Timeline column */}
            <div className="flex flex-col items-center">
              <div
                className={`w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-xs font-bold transition-all duration-500 ${
                  done   ? "bg-green-500 text-white" :
                  active ? "bg-blue-500 text-white animate-pulse scale-110" :
                           "bg-slate-200 text-slate-400"
                }`}
              >
                {done ? "✓" : i + 1}
              </div>
              {!last && (
                <div
                  className={`w-px flex-1 min-h-[20px] my-1 transition-colors duration-700 ${
                    done ? "bg-green-300" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
            {/* Label */}
            <div className={`flex items-start ${last ? "" : "pb-4"}`}>
              <span
                className={`text-sm pt-0.5 transition-all duration-300 ${
                  done   ? "text-slate-400 line-through" :
                  active ? "text-slate-900 font-semibold" :
                           "text-slate-300"
                }`}
              >
                {s.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SourceCard({
  source,
  index,
  gradient,
}: {
  source: QueryResponse["sources"][number];
  index: number;
  gradient: string;
}) {
  const displayPath = source.page_url.replace(/^https?:\/\/[^/]+\//, "");

  return (
    <a
      href={source.page_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative flex flex-col gap-2 bg-white rounded-xl border border-slate-200 p-4 hover:border-transparent hover:shadow-lg hover:shadow-slate-200/80 transition-all duration-200 overflow-hidden"
    >
      <div
        className={`absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r ${gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-200`}
      />
      <div className="flex items-start gap-2.5">
        <span
          className={`shrink-0 text-xs font-mono font-bold bg-gradient-to-br ${gradient} bg-clip-text text-transparent`}
        >
          [{index + 1}]
        </span>
        <span className="text-sm font-medium text-slate-800 group-hover:text-slate-900 transition-colors line-clamp-2 leading-snug">
          {source.section}
        </span>
      </div>
      <p className="text-xs text-slate-400 truncate pl-7 font-mono">{displayPath}</p>
    </a>
  );
}

const DAILY_LIMIT = 5;
const RL_KEY = "dn_usage";

function getRateLimit(): { count: number; date: string } {
  try {
    const raw = localStorage.getItem(RL_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { count: 0, date: "" };
}

function incrementRateLimit(): number {
  const today = new Date().toISOString().slice(0, 10);
  const prev = getRateLimit();
  const count = prev.date === today ? prev.count + 1 : 1;
  try {
    localStorage.setItem(RL_KEY, JSON.stringify({ count, date: today }));
  } catch {}
  return count;
}

function getRemainingQueries(): number {
  const today = new Date().toISOString().slice(0, 10);
  const { count, date } = getRateLimit();
  return date === today ? Math.max(0, DAILY_LIMIT - count) : DAILY_LIMIT;
}

function RateLimitModal({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-7 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center shrink-0 text-xl">
            ⚡
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">Daily limit reached</h2>
            <p className="text-sm text-slate-500">5 questions per day</p>
          </div>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          This is a portfolio demo running on live AI infrastructure — each
          question calls the Claude API and a vector database, so queries are
          capped at <strong>5 per day</strong> per visitor to keep it free to
          use. The limit resets at midnight.
        </p>
        <p className="text-sm text-slate-500">
          Want to dig deeper?{" "}
          <a
            href="https://github.com/kylemacasillitan/docs-navigator"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline font-medium"
          >
            Clone the repo
          </a>{" "}
          and run it locally with your own API keys.
        </p>
        <button
          onClick={onClose}
          className="mt-1 w-full py-2 rounded-xl bg-slate-900 text-white text-sm font-medium hover:bg-slate-700 transition-colors"
        >
          Got it
        </button>
      </div>
    </div>
  );
}

export default function Home() {
  const [libraryId, setLibraryId] = useState("nextjs");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRateLimit, setShowRateLimit] = useState(false);
  const [remaining, setRemaining] = useState(DAILY_LIMIT);

  useEffect(() => {
    setRemaining(getRemainingQueries());
  }, []);

  const activeLib = LIBRARIES.find((l) => l.id === libraryId)!;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    if (getRemainingQueries() <= 0) {
      setShowRateLimit(true);
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await queryDocs(libraryId, question.trim());
      const newCount = incrementRateLimit();
      setRemaining(Math.max(0, DAILY_LIMIT - newCount));
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const switchLibrary = (id: string) => {
    setLibraryId(id);
    setResult(null);
    setError(null);
  };

  const hasResult = result || isLoading || error;

  return (
    <div className="min-h-screen flex flex-col">
      {showRateLimit && <RateLimitModal onClose={() => setShowRateLimit(false)} />}

      {/* Gradient accent bar — changes with library */}
      <div className={`h-1 w-full bg-gradient-to-r ${activeLib.gradient} transition-all duration-500`} />

      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200/80">
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-6 h-6 rounded-md bg-gradient-to-br ${activeLib.gradient} transition-all duration-500 shadow-sm`}
            />
            <span className="text-base font-semibold text-slate-900 tracking-tight">
              Docs Navigator
            </span>
          </div>
          <div className="flex gap-1.5">
            {LIBRARIES.map((lib) => (
              <button
                key={lib.id}
                onClick={() => switchLibrary(lib.id)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-all duration-200 ${
                  libraryId === lib.id
                    ? `${lib.activeClass} shadow-md`
                    : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {lib.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Hero */}
        {!hasResult && (
          <div className="text-center pt-12 pb-2 flex flex-col items-center gap-5">
            <h1 className="text-4xl font-bold text-slate-900 tracking-tight leading-tight">
              Ask anything about{" "}
              <span
                className={`bg-gradient-to-r ${activeLib.gradient} bg-clip-text text-transparent transition-all duration-500`}
              >
                {activeLib.label}
              </span>
            </h1>
            <div className="flex flex-wrap justify-center gap-2">
              {activeLib.examples.map((ex) => (
                <button
                  key={ex}
                  onClick={() => setQuestion(ex)}
                  className="px-3.5 py-1.5 text-sm text-slate-600 bg-white border border-slate-200 rounded-full hover:border-slate-300 hover:shadow-sm hover:text-slate-900 transition-all duration-150"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Question form */}
        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-1 focus-within:border-transparent transition-all duration-200">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              placeholder={`Ask a question about ${activeLib.label}…`}
              rows={3}
              className="w-full px-5 py-4 text-slate-900 placeholder:text-slate-400 resize-none focus:outline-none text-base bg-transparent"
            />
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 bg-slate-50/50">
              <span className="text-xs text-slate-400">
                {remaining <= 0 ? (
                  <span className="text-amber-500 font-medium">Daily limit reached — resets at midnight</span>
                ) : (
                  <>
                    Press{" "}
                    <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-500 font-mono text-xs">
                      Enter
                    </kbd>{" "}
                    to send ·{" "}
                    <span className={remaining <= 2 ? "text-amber-500 font-medium" : ""}>
                      {remaining} of {DAILY_LIMIT} left today
                    </span>
                  </>
                )}
              </span>
              <button
                type="submit"
                disabled={isLoading || !question.trim() || remaining <= 0}
                className={`px-4 py-1.5 text-white text-sm font-medium rounded-lg transition-all duration-200 bg-gradient-to-r ${activeLib.gradient} hover:opacity-90 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {isLoading ? "Searching…" : "Ask →"}
              </button>
            </div>
          </div>
        </form>

        {/* Loading progress */}
        {isLoading && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-8 py-7">
            <ProgressLoader />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl px-5 py-4 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="flex flex-col gap-6">
            {/* Answer */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className={`h-1 w-full bg-gradient-to-r ${activeLib.gradient}`} />
              <div className="px-7 pt-5 pb-1">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                  Answer
                </span>
              </div>
              <div className="px-7 pb-7">
                <div className="prose prose-slate prose-sm max-w-none prose-code:before:content-none prose-code:after:content-none prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-slate-800 prose-code:font-mono prose-pre:bg-slate-900 prose-pre:text-slate-100">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {result.answer}
                  </ReactMarkdown>
                </div>
              </div>
            </div>

            {/* Sources */}
            <div>
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3 px-1">
                Sources
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {result.sources.map((source, i) => (
                  <SourceCard
                    key={i}
                    source={source}
                    index={i}
                    gradient={activeLib.gradient}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Built with Qdrant · BGE-M3
          </span>
          <span className="text-xs text-slate-400">Hybrid search + reranking</span>
        </div>
      </footer>
    </div>
  );
}
