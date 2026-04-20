import { useState, type FormEvent } from "react";
import { Plus, UserPlus } from "lucide-react";

import type { PatientCreateInput } from "../lib/types";

type Props = {
  isSubmitting: boolean;
  onCreate: (payload: PatientCreateInput) => Promise<void>;
};

type FormState = {
  fullName: string;
  age: string;
  gender: string;
  preferredLanguage: string;
};

const initialFormState: FormState = {
  fullName: "",
  age: "",
  gender: "",
  preferredLanguage: "",
};

export default function NewPatientForm({ isSubmitting, onCreate }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    if (!formState.fullName.trim()) {
      setLocalError("Full name is required.");
      return;
    }

    const payload: PatientCreateInput = {
      full_name: formState.fullName.trim(),
      age: formState.age ? Number(formState.age) : undefined,
      gender: formState.gender || undefined,
      preferred_language: formState.preferredLanguage || undefined,
    };

    try {
      await onCreate(payload);
      setFormState(initialFormState);
      setIsOpen(false);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Unable to create patient.");
    }
  }

  return (
    <div className="glass-panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Patient Intake</p>
          <h3 className="text-lg font-bold text-ink">Add a new patient chart</h3>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          onClick={() => {
            setLocalError(null);
            setIsOpen((current) => !current);
          }}
          type="button"
        >
          <Plus className="h-4 w-4" />
          {isOpen ? "Close" : "New Patient"}
        </button>
      </div>

      {isOpen ? (
        <form className="grid gap-3 md:grid-cols-2" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-700">Full Name</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent"
              placeholder="Patient full name"
              value={formState.fullName}
              onChange={(event) => setFormState((current) => ({ ...current, fullName: event.target.value }))}
            />
          </label>

          <div className="rounded-2xl bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800 md:col-span-2">
            Patient ID is generated automatically after chart creation.
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-700">Age</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent"
              inputMode="numeric"
              min="0"
              placeholder="42"
              type="number"
              value={formState.age}
              onChange={(event) => setFormState((current) => ({ ...current, age: event.target.value }))}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-slate-700">Gender</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent"
              value={formState.gender}
              onChange={(event) => setFormState((current) => ({ ...current, gender: event.target.value }))}
            >
              <option value="">Select</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label className="block md:col-span-2">
            <span className="mb-2 block text-sm font-semibold text-slate-700">Preferred Language</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-accent"
              value={formState.preferredLanguage}
              onChange={(event) =>
                setFormState((current) => ({ ...current, preferredLanguage: event.target.value }))
              }
            >
              <option value="">Select</option>
              <option value="english">English</option>
              <option value="hindi">Hindi</option>
              <option value="marathi">Marathi</option>
            </select>
          </label>

          {localError ? (
            <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 md:col-span-2">
              {localError}
            </div>
          ) : null}

          <div className="md:col-span-2">
            <button
              className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={isSubmitting}
              type="submit"
            >
              <UserPlus className="h-4 w-4" />
              {isSubmitting ? "Creating..." : "Create Patient"}
            </button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-slate-600">
          Create a patient chart without leaving the doctor dashboard.
        </p>
      )}
    </div>
  );
}
