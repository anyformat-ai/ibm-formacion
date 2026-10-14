"use client";

import { useState } from "react";
import type { DocumentResult, Job, WorkflowSummary } from "@/lib/types";
import { ResultCard } from "./ResultCard";
import { Uploader } from "./Uploader";
import { WorkflowPicker } from "./WorkflowPicker";

export function DocumentApp({
  workflows,
  defaultWorkflowId,
}: {
  workflows: WorkflowSummary[];
  defaultWorkflowId: string | null;
}) {
  const [workflowId, setWorkflowId] = useState(defaultWorkflowId ?? workflows[0]?.id ?? "");
  const [threshold, setThreshold] = useState(85);
  const [jobs, setJobs] = useState<Job[]>([]);

  function update(id: string, patch: Partial<Job>) {
    setJobs((all) => all.map((j) => (j.id === id ? ({ ...j, ...patch } as Job) : j)));
  }

  // Cada fichero va en su propia petición, en paralelo: cada tarjeta avanza a su ritmo.
  async function runFile(file: File) {
    const id = `${Date.now()}-${Math.random()}`;
    setJobs((all) => [{ id, fileName: file.name, startedAt: Date.now(), status: "processing" }, ...all]);

    const body = new FormData();
    body.set("file", file);
    body.set("workflowId", workflowId);
    try {
      const res = await fetch("/api/run", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `Error ${res.status}`);
      update(id, { status: "done", result: data as DocumentResult });
    } catch (err) {
      update(id, { status: "error", error: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <section className="flex flex-wrap items-end gap-6">
        <WorkflowPicker workflows={workflows} value={workflowId} onChange={setWorkflowId} />
        <label className="flex flex-col gap-1.5">
          <span className="label">
            Umbral de confianza: <span className="font-mono text-ink">{threshold}</span>
          </span>
          <input
            type="range"
            min={0}
            max={100}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="h-8 w-56"
          />
        </label>
      </section>

      <Uploader disabled={!workflowId} onFiles={(files) => files.forEach(runFile)} />

      {jobs.map((job) => (
        <ResultCard key={job.id} {...job} threshold={threshold} />
      ))}
    </div>
  );
}
