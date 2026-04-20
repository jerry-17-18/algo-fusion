type Props = {
  isRecording: boolean;
  isConnected: boolean;
  statusText: string;
  speechLanguage: string;
  onSpeechLanguageChange: (language: string) => void;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
};

export default function RecordingControls({
  isRecording,
  isConnected,
  statusText,
  speechLanguage,
  onSpeechLanguageChange,
  onStart,
  onStop,
}: Props) {
  return (
    <div className="glass-panel flex flex-col gap-4 p-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Capture</p>
        <h3 className="text-lg font-bold text-ink">Record consultation for Sarvam transcription</h3>
      </div>

      <div className="flex items-center gap-3">
        <button
          className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={isRecording}
          onClick={() => void onStart()}
        >
          Start Recording
        </button>
        <button
          className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={!isRecording}
          onClick={() => void onStop()}
        >
          Stop Recording
        </button>
      </div>

      <label className="block">
        <span className="mb-2 block text-sm font-semibold text-slate-700">Consultation language hint</span>
        <select
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-accent"
          disabled={isRecording}
          value={speechLanguage}
          onChange={(event) => onSpeechLanguageChange(event.target.value)}
        >
          <option value="en-IN">English (India)</option>
          <option value="hi-IN">Hindi</option>
          <option value="mr-IN">Marathi</option>
        </select>
      </label>

      <div className="rounded-2xl bg-slate-900 px-4 py-3 font-mono text-xs text-slate-100">
        Pipeline: {isConnected ? "recording" : "idle"} | Transcript mode: full-session Sarvam upload
      </div>

      <p className="text-sm text-slate-600">{statusText}</p>
    </div>
  );
}
