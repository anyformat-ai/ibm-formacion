"use client";

import { useRef, useState } from "react";

/** Zona para arrastrar o elegir uno o varios PDFs. */
export function Uploader({ disabled, onFiles }: { disabled: boolean; onFiles: (files: File[]) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  function take(list: FileList | null) {
    const files = Array.from(list ?? []).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    if (files.length && !disabled) onFiles(files);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
      className={`flex flex-col items-center gap-3 rounded-card border border-dashed px-6 py-10 text-center transition-colors ${
        over ? "border-accent bg-accent-soft" : "border-hair-3 bg-surface"
      }`}
    >
      <p className="text-[14px] font-medium">Arrastra aquí tus PDFs</p>
      <p className="text-[12.5px] text-ink-3">Uno o varios. Cada documento se procesa por separado.</p>
      <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => input.current?.click()}>
        Elegir ficheros
      </button>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(e) => {
          take(e.target.files);
          e.target.value = ""; // permite volver a elegir el mismo fichero
        }}
      />
    </div>
  );
}
