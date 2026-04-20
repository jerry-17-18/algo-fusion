import { Download, History } from "lucide-react";

import type { PatientHistory } from "../lib/types";

type Props = {
  history: PatientHistory | null;
  disabled: boolean;
  onLoad: () => Promise<void>;
  onDownload: () => Promise<void>;
  onDownloadReport: (recordId: string) => Promise<void>;
};

export default function PatientHistoryPanel({ history, disabled, onLoad, onDownload, onDownloadReport }: Props) {
  return (
    <section className="glass-panel p-5">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Patient History</p>
          <h3 className="text-lg font-bold text-ink">Mapped DB records</h3>
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={disabled}
            onClick={() => void onLoad()}
            type="button"
          >
            <History className="h-4 w-4" />
            Load History
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={disabled}
            onClick={() => void onDownload()}
            type="button"
          >
            <Download className="h-4 w-4" />
            Download JSON
          </button>
        </div>
      </div>

      <div className="max-h-[360px] space-y-3 overflow-auto">
        {history?.records.length ? (
          history.records.map((record) => (
            <article key={record.id} className="rounded-2xl bg-slate-50 p-4">
              <div className="mb-2 flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                <span>{new Date(record.created_at).toLocaleString()}</span>
                <span>Session {record.session_id.slice(0, 8)}</span>
              </div>
              <p className="mb-3 text-sm text-slate-700">
                {record.raw_transcript || "No transcript captured for this record."}
              </p>
              <div className="grid gap-2 text-sm md:grid-cols-2">
                <HistoryItem label="Symptoms" value={record.structured_data.symptoms.join(", ") || "Not captured"} />
                <HistoryItem label="Duration" value={record.structured_data.duration || "Not captured"} />
                <HistoryItem label="Diagnosis" value={record.structured_data.diagnosis || "Not captured"} />
                <HistoryItem label="Medications" value={record.structured_data.medications.join(", ") || "Not captured"} />
              </div>
              <div className="mt-3">
                <button
                  className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
                  onClick={() => void onDownloadReport(record.id)}
                  type="button"
                >
                  <Download className="h-4 w-4" />
                  Download PDF Report
                </button>
              </div>
            </article>
          ))
        ) : (
          <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
            Load the selected patient history to view mapped records from the database.
          </p>
        )}
      </div>
    </section>
  );
}

function HistoryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="font-medium text-ink">{value}</p>
    </div>
  );
}
