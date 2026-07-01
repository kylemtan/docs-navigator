"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { queryDocs, type QueryResponse } from "@/lib/api";

const LIBRARIES = [{ id: "nextjs", label: "Next.js" }];

function SkeletonLoader() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-3/4" />
      <div className="h-4 bg-slate-200 rounded" />
      <div className="h-4 bg-slate-200 rounded w-5/6" />
      <div className="h-4 bg-slate-200 rounded w-2/3" />
      <div className="h-4 bg-slate-200 rounded w-4/5" />
      <div className="mt-6 h-4 bg-slate-200 rounded w-1/2" />
      <div className="h-4 bg-slate-200 rounded w-3/4" />
      <div className="h-4 bg-slate-200 rounded" />
    </div>
  );
}

function SourceCard({
  source,
  index,
}: {
  source: QueryResponse["sources"][number];
  index: number;
}) {
  const path = source.page_url.replace("https://nextjs.org/docs/", "");

  return (
    <a
      href={source.page_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col gap-2 bg-white rounded-xl border border-slate-200 p-4 hover:border-blue-300 hover:shadow-md transition-all duration-150"
    >
      <div className="flex items-start gap-2.5">
        <span className="shrink-0 text-xs font-mono font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
          [{index + 1}]
        </span>
        <span className="text-sm font-medium text-slate-800 group-hover:text-blue-600 transition-colors line-clamp-2 leading-snug">
          {source.section}
        </span>
      </div>
      <p className="text-xs text-slate-400 truncate pl-9">{path}</p>
    </a>
  );
}

export default function Home() {
  const [library, setLibrary] = useState("nextjs");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await queryDocs(library, question.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const hasResult = result || isLoading || error;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-base font-semibold text-slate-900 tracking-tight">
            Docs Navigator
          </span>
          <div className="flex gap-1.5">
            {LIBRARIES.map((lib) => (
              <button
                key={lib.id}
                onClick={() => setLibrary(lib.id)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  library === lib.id
                    ? "bg-blue-600 text-white"
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
        {/* Hero — only visible before first query */}
        {!hasResult && (
          <div className="text-center pt-12 pb-4">
            <h1 className="text-3xl font-semibold text-slate-900 mb-2 tracking-tight">
              Ask anything about{" "}
              <span className="text-blue-600">Next.js</span>
            </h1>
            <p className="text-slate-500 text-base">
              Answers sourced directly from the official documentation.
            </p>
          </div>
        )}

        {/* Question form */}
        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-1 transition-shadow">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              placeholder="How do I use server actions?"
              rows={3}
              className="w-full px-5 py-4 text-slate-900 placeholder:text-slate-400 resize-none focus:outline-none text-base bg-transparent"
            />
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 bg-slate-50/50">
              <span className="text-xs text-slate-400">
                Press{" "}
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-500 font-mono text-xs">
                  Enter
                </kbd>{" "}
                to send
              </span>
              <button
                type="submit"
                disabled={isLoading || !question.trim()}
                className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? "Searching…" : "Ask →"}
              </button>
            </div>
          </div>
        </form>

        {/* Loading skeleton */}
        {isLoading && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-6 py-6">
            <SkeletonLoader />
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
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-7 py-6">
              <div className="prose prose-slate prose-sm max-w-none prose-code:before:content-none prose-code:after:content-none prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-slate-800 prose-code:font-mono prose-pre:bg-slate-900 prose-pre:text-slate-100">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.answer}
                </ReactMarkdown>
              </div>
            </div>

            {/* Sources */}
            <div>
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3 px-1">
                Sources
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {result.sources.map((source, i) => (
                  <SourceCard key={i} source={source} index={i} />
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
