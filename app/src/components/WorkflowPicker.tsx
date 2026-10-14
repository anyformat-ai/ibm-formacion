import type { WorkflowSummary } from "@/lib/types";

export function WorkflowPicker({
  workflows,
  value,
  onChange,
}: {
  workflows: WorkflowSummary[];
  value: string;
  onChange: (id: string) => void;
}) {
  // Si ANYFORMAT_WORKFLOW_ID no está en la lista (p. ej. de otra página), lo mostramos igualmente.
  const options = value && !workflows.some((w) => w.id === value)
    ? [{ id: value, name: `${value} (de .env.local)` }, ...workflows]
    : workflows;

  return (
    <label className="flex flex-col gap-1.5">
      <span className="label">Workflow</span>
      <select className="control min-w-72" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.length === 0 && <option value="">No hay workflows en esta cuenta</option>}
        {options.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
    </label>
  );
}
