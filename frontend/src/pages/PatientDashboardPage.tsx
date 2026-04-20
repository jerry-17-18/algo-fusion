import { useEffect, useState } from "react";
import { Download, FileText, LogOut, UserRound } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { apiClient } from "../lib/api";
import type { PatientPortalDashboard } from "../lib/types";

export default function PatientDashboardPage() {
  const { user, logout } = useAuth();
  const [dashboard, setDashboard] = useState<PatientPortalDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    apiClient
      .getPatientPortalDashboard()
      .then((response) => {
        if (!cancelled) {
          setDashboard(response);
          setError(null);
        }
      })
      .catch((fetchError) => {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "Unable to load patient reports");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleDownloadReport(recordId: string) {
    try {
      setDownloadingId(recordId);
      setError(null);
      const blob = await apiClient.downloadPatientPortalReport(recordId);
      const filename = `${dashboard?.patient.external_id ?? "patient"}-${recordId.slice(0, 8)}-report.pdf`;
      downloadBlob(blob, filename);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Unable to download report");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 glass-panel flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-3xl bg-teal-100 p-4 text-teal-800">
              <UserRound className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Patient Dashboard</p>
              <h1 className="text-3xl font-extrabold text-ink">Your visit reports</h1>
              <p className="text-sm text-slate-600">
                Signed in as {user?.full_name ?? "Patient"}
                {dashboard?.patient.external_id ? ` • ID ${dashboard.patient.external_id}` : ""}
              </p>
            </div>
          </div>

          <button
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            onClick={logout}
            type="button"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </header>

        {error ? <div className="mb-6 rounded-3xl bg-rose-50 px-5 py-4 text-sm font-medium text-rose-700">{error}</div> : null}

        <section className="mb-6 grid gap-4 md:grid-cols-2">
          <div className="glass-panel p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Profile</p>
            <h2 className="mb-4 text-xl font-bold text-ink">Patient details</h2>
            <div className="grid gap-3 text-sm md:grid-cols-2">
              <ProfileItem label="Name" value={dashboard?.patient.full_name ?? user?.full_name ?? "Loading..."} />
              <ProfileItem label="Patient ID" value={dashboard?.patient.external_id ?? user?.external_id ?? "Loading..."} />
              <ProfileItem label="Age" value={dashboard?.patient.age?.toString() ?? user?.age?.toString() ?? "Not provided"} />
              <ProfileItem label="Sex" value={dashboard?.patient.gender ?? user?.gender ?? "Not provided"} />
            </div>
          </div>

          <div className="glass-panel p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Access</p>
            <h2 className="mb-3 text-xl font-bold text-ink">Reports by visit</h2>
            <p className="text-sm text-slate-600">
              Download a PDF summary for each clinical visit, including symptoms, duration, diagnosis, and medications.
            </p>
          </div>
        </section>

        <section className="glass-panel p-5">
          <div className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Reports</p>
            <h2 className="text-xl font-bold text-ink">Visit history</h2>
          </div>

          {loading ? (
            <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">Loading your reports...</p>
          ) : dashboard?.reports.length ? (
            <div className="space-y-4">
              {dashboard.reports.map((report) => (
                <article key={report.id} className="rounded-2xl bg-slate-50 p-4">
                  <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Visit {new Date(report.created_at).toLocaleString()}
                      </p>
                      <h3 className="text-lg font-bold text-ink">Clinical report</h3>
                    </div>
                    <button
                      className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                      disabled={downloadingId === report.id}
                      onClick={() => void handleDownloadReport(report.id)}
                      type="button"
                    >
                      <Download className="h-4 w-4" />
                      {downloadingId === report.id ? "Preparing PDF..." : "Download PDF"}
                    </button>
                  </div>

                  <div className="grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-4">
                    <ProfileItem label="Symptoms" value={report.structured_data.symptoms.join(", ") || "Not captured"} />
                    <ProfileItem label="Duration" value={report.structured_data.duration || "Not captured"} />
                    <ProfileItem label="Diagnosis" value={report.structured_data.diagnosis || report.suggested_diagnosis || "Not captured"} />
                    <ProfileItem label="Medications" value={report.structured_data.medications.join(", ") || "Not captured"} />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl bg-slate-50 p-8 text-center">
              <FileText className="mx-auto mb-3 h-8 w-8 text-slate-400" />
              <p className="text-sm text-slate-600">No visit reports are available yet for this patient account.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function ProfileItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
