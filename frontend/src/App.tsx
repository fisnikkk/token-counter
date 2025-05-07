import { useEffect, useState } from "react";

const MODELS = [
  { id: "openai", label: "OpenAI",  limit: 128_000 },  // GPT-4o & 3.5-turbo-128k
  { id: "claude", label: "Claude",  limit: 200_000 },  // Claude-3 Opus / Sonnet
  { id: "gemini", label: "Gemini",  limit: 1_000_000 },// Gemini-1.5-Pro (≈1 M)
  { id: "llama",  label: "Llama-2", limit: 4_096   },  // Llama-2-Chat-7B-4K
] as const;

function limitOf(id: string) {
  const m = MODELS.find(m => m.id === id);
  return m ? m.limit.toLocaleString() : "—";
}


export default function App() {
  const [text, setText]     = useState("");
  const [model, setModel]   = useState("openai");   // ←  add back
  const [chatMode, setChatMode] = useState(false);
  const [tokens, setTokens] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  async function count() {
    if (!text.trim()) { setTokens(null); return; }
    setLoading(true);

    try {
      const endpoint = chatMode ? "/chat-count" : "/count";
      const payload  = chatMode
        ? {
            messages: [
              { role: "system", content: "You are helpful." },
              { role: "user",   content: text }
            ],
            model
          }
        : { text, model };

      const res  = await fetch(import.meta.env.VITE_API_URL + endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      setTokens(data.tokens);

    } catch (e) {
      alert("API error: " + e);
      setTokens(null);
    }
    setLoading(false);
  }

  /* auto-count after typing or switching model/chatMode */
  useEffect(() => {
    const id = setTimeout(count, 500);
    return () => clearTimeout(id);
  }, [text, model, chatMode]);


  return (
    <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center">
      <h1 className="text-3xl font-bold mb-4">💠 Token Counter</h1>

      <label className="mb-2 flex items-center gap-2">
  <input
    type="checkbox"
    checked={chatMode}
    onChange={e => setChatMode(e.target.checked)}
  />
  Count **full chat prompt** (adds hidden system / role tokens)
</label>



      <textarea
        className="w-full max-w-3xl h-48 p-3 border rounded resize-y focus:outline-blue-500"
        placeholder="Paste or type text here…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />

      <p className="mt-1 text-sm text-gray-500">
        Context limits → OpenAI: <b>{limitOf("openai")}</b> • Claude: <b>{limitOf("claude")}</b> •
        Gemini: <b>{limitOf("gemini")}</b> • Llama-2: <b>{limitOf("llama")}</b> tokens
      </p>

      <div className="flex flex-wrap gap-2 mt-3">
        {MODELS.map((m) => (
          <button
            key={m.id}
            onClick={() => setModel(m.id)}
            className={`px-4 py-2 rounded-full ${
              model === m.id
                ? "bg-blue-600 text-white"
                : "bg-white border hover:bg-gray-100"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <p className="mt-6 text-xl">
        {loading ? "Counting…" : tokens !== null && `Tokens: ${tokens}`}
      </p>

      <footer className="mt-auto text-sm text-gray-500 pt-8">
        Tokenization&nbsp;©&nbsp;2025
      </footer>
    </div>
  );
}
