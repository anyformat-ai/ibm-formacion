// POST /api/run — multipart con `file` (un PDF) y `workflowId`. Devuelve un DocumentResult.
import { errorMessage, runDocument } from "@/lib/anyformat";

export const runtime = "nodejs";
export const maxDuration = 300; // segundos: un run de varias páginas puede tardar minutos

export async function POST(req: Request) {
  const form = await req.formData();
  const file = form.get("file");
  const workflowId = form.get("workflowId");

  if (!(file instanceof File)) return Response.json({ error: "Falta el fichero" }, { status: 400 });
  if (typeof workflowId !== "string" || !workflowId) {
    return Response.json({ error: "Elige un workflow" }, { status: 400 });
  }

  try {
    return Response.json(await runDocument(workflowId, file));
  } catch (err) {
    console.error("[api/run]", err);
    return Response.json({ error: errorMessage(err) }, { status: 502 });
  }
}
