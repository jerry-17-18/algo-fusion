import type { DoctorAssist } from "../lib/types";

type Props = {
  assist: DoctorAssist;
};

export default function DoctorAssistPanel({ assist }: Props) {
  return (
    <section className="glass-panel p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Doctor Assist</p>
        <h3 className="text-lg font-bold text-ink">Suggested diagnosis and gaps</h3>
      </div>

      <div className="mb-4 rounded-2xl bg-teal-50 p-4">
        <p className="mb-1 text-xs font-semibold uppercase tracking-[0.24em] text-teal-700">Suggested diagnosis</p>
        <p className="text-sm font-semibold text-teal-950">
          {assist.suggested_diagnosis || "Waiting for enough clinical context"}
        </p>
      </div>

      <div className="space-y-3">
        <div className="rounded-2xl bg-white/80 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Missing fields</p>
          <div className="flex flex-wrap gap-2">
            {assist.missing_fields.length ? (
              assist.missing_fields.map((field) => (
                <span key={field} className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                  {field}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">No major gaps flagged.</span>
            )}
          </div>
        </div>

        <div className="rounded-2xl bg-white/80 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Red flags</p>
          <div className="flex flex-wrap gap-2">
            {assist.red_flags.length ? (
              assist.red_flags.map((flag) => (
                <span key={flag} className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-800">
                  {flag}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">No red flags currently grounded in the transcript.</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

