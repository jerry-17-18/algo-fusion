import { useState } from "react";

import type { RagAnswer } from "../lib/types";

type Props = {
  disabled: boolean;
  answer: RagAnswer | null;
  onSubmit: (question: string) => Promise<void>;
};

export default function RagChatPanel({ disabled, answer, onSubmit }: Props) {
  const [question, setQuestion] = useState("");

  return (
    <section className="glass-panel p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">RAG Chatbot</p>
        <h3 className="text-lg font-bold text-ink">Ask grounded history questions</h3>
      </div>

      <form
        className="mb-4 flex gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (!question.trim()) {
            return;
          }
          void onSubmit(question);
        }}
      >
        <input
          className="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent"
          disabled={disabled}
          placeholder="Ask about past symptoms, medications, or prior diagnosis"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button
          className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={disabled || !question.trim()}
          type="submit"
        >
          Ask
        </button>
      </form>

      <div className="space-y-4">
        <div className="rounded-3xl bg-slate-950 p-4 text-sm leading-7 text-slate-100">
          {answer?.answer || "Grounded answers from prior session embeddings will appear here."}
        </div>

        <div className="space-y-3">
          {answer?.citations.map((citation) => (
            <div key={`${citation.record_id}-${citation.session_id}`} className="rounded-2xl bg-slate-50 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                Citation • score {citation.score.toFixed(3)}
              </p>
              <p className="text-sm text-slate-700">{citation.excerpt}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

