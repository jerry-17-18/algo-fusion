import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import type { Patient } from "../lib/types";

type Props = {
  patients: Patient[];
  selectedPatientId: string;
  onChange: (patientId: string) => void;
};

export default function PatientSelector({ patients, selectedPatientId, onChange }: Props) {
  const [lookupValue, setLookupValue] = useState("");
  const [lookupError, setLookupError] = useState<string | null>(null);

  useEffect(() => {
    const selectedPatient = patients.find((patient) => patient.id === selectedPatientId);
    if (selectedPatient) {
      setLookupValue(selectedPatient.external_id);
      setLookupError(null);
    }
  }, [patients, selectedPatientId]);

  function handleLookupSelection() {
    const normalized = lookupValue.trim().toLowerCase();
    if (!normalized) {
      setLookupError("Enter a patient ID to select a chart.");
      return;
    }

    const match = patients.find(
      (patient) =>
        patient.external_id.toLowerCase() === normalized ||
        patient.id.toLowerCase() === normalized,
    );
    if (!match) {
      setLookupError("No patient matches that ID.");
      return;
    }

    setLookupError(null);
    onChange(match.id);
  }

  return (
    <div className="glass-panel p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Patient</p>
          <h3 className="text-lg font-bold text-ink">Select active chart</h3>
        </div>
      </div>

      <div className="mb-3 flex gap-3">
        <input
          className="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-accent"
          placeholder="Enter patient ID or UUID"
          value={lookupValue}
          onChange={(event) => {
            setLookupValue(event.target.value);
            if (lookupError) {
              setLookupError(null);
            }
          }}
        />
        <button
          className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          onClick={handleLookupSelection}
          type="button"
        >
          <Search className="h-4 w-4" />
          Select by ID
        </button>
      </div>

      {lookupError ? <p className="mb-3 text-sm font-medium text-rose-700">{lookupError}</p> : null}

      <select
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none ring-0 transition focus:border-accent"
        value={selectedPatientId}
        onChange={(event) => {
          setLookupError(null);
          onChange(event.target.value);
        }}
      >
        <option value="">Choose patient</option>
        {patients.map((patient) => (
          <option key={patient.id} value={patient.id}>
            {patient.external_id} • {patient.full_name}
          </option>
        ))}
      </select>
    </div>
  );
}
