import { DocumentApp } from "@/components/DocumentApp";
import { errorMessage, listWorkflows } from "@/lib/anyformat";
import type { WorkflowSummary } from "@/lib/types";

// Se renderiza en cada petición: la lista de workflows sale de la cuenta en vivo.
export const dynamic = "force-dynamic";

export default async function Home() {
  let workflows: WorkflowSummary[] = [];
  let error: string | null = null;
  try {
    workflows = await listWorkflows();
  } catch (err) {
    error = errorMessage(err);
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="rounded-window bg-canvas shadow-window">
        <header className="flex items-center justify-between gap-4 border-b border-hair px-6 py-4">
          <div>
            <h1 className="text-[17px] font-semibold tracking-tight">Extracción de documentos</h1>
            <p className="text-[13px] text-ink-2">
              Sube PDFs, ejecuta un workflow de anyformat y revisa lo extraído campo a campo.
            </p>
          </div>
          <span className="font-mono text-[12px] text-ink-3">anyformat</span>
        </header>

        {error ? (
          <div className="m-6 rounded-card bg-danger-soft p-4 text-[13px] text-danger">
            No se pudo hablar con anyformat: {error}
            <br />
            Copia <code>.env.example</code> a <code>.env.local</code>, pon tu API key y reinicia <code>bun dev</code>.
          </div>
        ) : (
          <DocumentApp workflows={workflows} defaultWorkflowId={process.env.ANYFORMAT_WORKFLOW_ID || null} />
        )}
      </div>
    </main>
  );
}
