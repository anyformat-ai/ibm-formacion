import type { Field, FieldValue } from "./types";

/** Un valor está "a revisar" si tiene confianza y queda por debajo del umbral (y nadie lo ha corregido ya). */
export function needsReview(v: FieldValue, threshold: number): boolean {
  return !v.corrected && v.confidence !== null && v.confidence < threshold;
}

/** Cuenta los valores a revisar, incluidas las celdas de los campos objeto. */
export function countToReview(fields: Field[], threshold: number): number {
  return fields.reduce((n, f) => {
    if (f.kind === "scalar") return n + (needsReview(f, threshold) ? 1 : 0);
    return n + f.rows.flatMap((row) => Object.values(row)).filter((v) => needsReview(v, threshold)).length;
  }, 0);
}
