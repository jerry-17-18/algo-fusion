import type { StructuredClinicalData } from "../lib/types";

type Props = {
  data: StructuredClinicalData;
};

const fallback: StructuredClinicalData = {
  symptoms: [],
  duration: "",
  diagnosis: "",
  medications: [],
};

export default function StructuredDataPanel({ data }: Props) {
  const value = data ?? fallback;

  return (
    <section className="glass-panel p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Structured JSON</p>
        <h3 className="text-lg font-bold text-ink">Clinical extraction</h3>
      </div>

      <div className="space-y-4 text-sm text-slate-700">
        <PanelRow label="Symptoms" value={value.symptoms.join(", ") || "Not captured yet"} />
        <PanelRow label="Duration" value={value.duration || "Not captured yet"} />
        <PanelRow label="Diagnosis" value={value.diagnosis || "Not captured yet"} />
        <PanelRow label="Medications" value={value.medications.join(", ") || "Not captured yet"} />
      </div>
    </section>
  );
}

function PanelRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

