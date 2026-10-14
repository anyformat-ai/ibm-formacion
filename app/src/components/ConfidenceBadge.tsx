/** Confianza 0–100 como insignia: verde si supera el umbral, ámbar si se acerca, rojo si no. */
export function ConfidenceBadge({ confidence, threshold }: { confidence: number | null; threshold: number }) {
  if (confidence === null) return <span className="text-ink-4">—</span>;

  const tone =
    confidence >= threshold
      ? "bg-success-soft text-success"
      : confidence >= threshold - 20
        ? "bg-warning-soft text-warning"
        : "bg-danger-soft text-danger";

  return (
    <span className={`inline-block rounded-badge px-1.5 py-px font-mono text-[11.5px] font-semibold ${tone}`}>
      {Math.round(confidence)}
    </span>
  );
}
