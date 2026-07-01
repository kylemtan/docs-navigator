const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface SourceChunk {
  page_url: string;
  section: string;
  text: string;
}

export interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
}

export async function queryDocs(
  library: string,
  question: string,
): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ library, question }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Query failed");
  }
  return res.json();
}
