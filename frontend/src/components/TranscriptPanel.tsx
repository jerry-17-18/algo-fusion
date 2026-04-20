type Props = {
  transcript: string;
  transcriptChunks: string[];
  languages: string[];
};

export default function TranscriptPanel({ transcript, transcriptChunks, languages }: Props) {
  return (
    <section className="glass-panel flex min-h-[420px] flex-col p-5">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Transcript</p>
          <h3 className="text-lg font-bold text-ink">Live consultation notes</h3>
        </div>
        <div className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
          {languages.length ? languages.join(", ") : "language pending"}
        </div>
      </div>

      <div className="mb-4 rounded-3xl bg-slate-950 p-4 text-sm leading-7 text-slate-100">
        {transcript || "The transcript will appear here after the full recording is sent to Sarvam."}
      </div>

      <div className="scroll-area flex-1 overflow-auto rounded-3xl border border-slate-200 bg-white/70 p-4">
        <div className="space-y-3">
          {transcriptChunks.length ? (
            transcriptChunks.map((chunk, index) => (
              <div key={`${chunk}-${index}`} className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                {chunk}
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">Processed transcript sections will appear here after transcription.</p>
          )}
        </div>
      </div>
    </section>
  );
}
