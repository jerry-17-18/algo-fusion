import { useState, type FormEvent } from "react";
import { Activity, ShieldCheck, UserRound } from "lucide-react";

import { useAuth } from "../context/AuthContext";

type LoginMode = "doctor" | "patient";

export default function LoginPage() {
  const { loginDoctor, loginPatient } = useAuth();
  const [mode, setMode] = useState<LoginMode>("doctor");
  const [doctorUsername, setDoctorUsername] = useState("doctor");
  const [doctorPassword, setDoctorPassword] = useState("doctor123");
  const [patientId, setPatientId] = useState("");
  const [patientName, setPatientName] = useState("");
  const [patientAge, setPatientAge] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleDoctorSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await loginDoctor(doctorUsername, doctorPassword);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Doctor login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handlePatientSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await loginPatient(patientId, patientName, Number(patientAge));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Patient login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-6xl gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="glass-panel overflow-hidden p-8 lg:p-12">
          <div className="mb-10 flex items-center gap-3">
            <div className="rounded-2xl bg-accent/10 p-3 text-accent">
              <Activity className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Clinical Voice AI</p>
              <h1 className="text-3xl font-extrabold text-ink lg:text-5xl">
                Consultation capture, visit reports, and patient-side access in one workspace.
              </h1>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              "Doctor dashboard with structured extraction",
              "Downloadable PDF report for every visit",
              "Patient portal for visit-wise report access",
            ].map((item) => (
              <div key={item} className="rounded-3xl bg-white/70 p-5">
                <p className="text-sm font-semibold text-slate-800">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel p-8">
          <div className="mb-6 flex gap-2 rounded-2xl bg-slate-100 p-1">
            <button
              className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                mode === "doctor" ? "bg-white text-slate-950 shadow-sm" : "text-slate-500"
              }`}
              onClick={() => {
                setMode("doctor");
                setError(null);
              }}
              type="button"
            >
              Doctor Login
            </button>
            <button
              className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                mode === "patient" ? "bg-white text-slate-950 shadow-sm" : "text-slate-500"
              }`}
              onClick={() => {
                setMode("patient");
                setError(null);
              }}
              type="button"
            >
              Patient Login
            </button>
          </div>

          {mode === "doctor" ? (
            <>
              <div className="mb-8 flex items-center gap-3">
                <div className="rounded-2xl bg-slate-900 p-3 text-white">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Doctor Login</p>
                  <h2 className="text-2xl font-bold text-ink">Secure access</h2>
                </div>
              </div>

              <form className="space-y-4" onSubmit={handleDoctorSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-slate-700">Username</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-accent"
                    value={doctorUsername}
                    onChange={(event) => setDoctorUsername(event.target.value)}
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-slate-700">Password</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-accent"
                    type="password"
                    value={doctorPassword}
                    onChange={(event) => setDoctorPassword(event.target.value)}
                  />
                </label>

                {error ? <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}

                <button
                  className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  disabled={loading}
                  type="submit"
                >
                  {loading ? "Signing in..." : "Sign in as doctor"}
                </button>
              </form>

              <div className="mt-6 rounded-2xl bg-teal-50 p-4 text-sm text-teal-800">
                Demo credentials are pre-seeded by default: <strong>doctor / doctor123</strong>
              </div>
            </>
          ) : (
            <>
              <div className="mb-8 flex items-center gap-3">
                <div className="rounded-2xl bg-teal-100 p-3 text-teal-800">
                  <UserRound className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Patient Login</p>
                  <h2 className="text-2xl font-bold text-ink">Open your report dashboard</h2>
                </div>
              </div>

              <form className="space-y-4" onSubmit={handlePatientSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-slate-700">Patient ID</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-accent"
                    placeholder="PAT-1001"
                    value={patientId}
                    onChange={(event) => setPatientId(event.target.value)}
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-slate-700">Full Name</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-accent"
                    placeholder="Patient name"
                    value={patientName}
                    onChange={(event) => setPatientName(event.target.value)}
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-slate-700">Age</span>
                  <input
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-accent"
                    inputMode="numeric"
                    min="0"
                    type="number"
                    value={patientAge}
                    onChange={(event) => setPatientAge(event.target.value)}
                  />
                </label>

                {error ? <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}

                <button
                  className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  disabled={loading || !patientId.trim() || !patientName.trim() || !patientAge}
                  type="submit"
                >
                  {loading ? "Opening dashboard..." : "Sign in as patient"}
                </button>
              </form>

              <div className="mt-6 rounded-2xl bg-teal-50 p-4 text-sm text-teal-800">
                Use the patient ID, full name, and age recorded in the clinic to open visit reports.
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
