"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api";

function LinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 17H7A5 5 0 0 1 7 7h2" />
      <path d="M15 7h2a5 5 0 1 1 0 10h-2" />
      <path d="M8 12h8" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M17 8l-5-5-5 5" />
      <path d="M12 3v12" />
    </svg>
  );
}

interface UploadResponse {
  success: boolean;
  trades_processed: number;
  trades_skipped: number;
  trades_failed: number;
  errors: string[];
}

/**
 * "Connect/Sync Broker" + "Upload Tradebook" action bar, shared between
 * /portfolio and /journal (identical behavior on both pages per BRD ask —
 * kept as one component instead of duplicating the upload panel twice).
 */
export function BrokerActionsBar({ onUploadSuccess }: { onUploadSuccess?: () => void }) {
  const router = useRouter();
  const [panelOpen, setPanelOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ tone: "gain" | "loss" | "estimate"; text: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function reset() {
    setFile(null);
    setMessage(null);
    setPanelOpen(false);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await apiFetch<UploadResponse>("/trades/upload-csv", {
        method: "POST",
        body: formData,
      });
      setMessage({
        tone: "gain",
        text: `Trades imported successfully — ${result.trades_processed} processed, ${result.trades_skipped} already existed, ${result.trades_failed} skipped. Refreshing…`,
      });
      setFile(null);
      onUploadSuccess?.();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setMessage({
          tone: "estimate",
          text: "CSV import is being set up. Please use the Brokers page to connect your broker account directly.",
        });
      } else {
        setMessage({
          tone: "loss",
          text: err instanceof Error ? err.message : "Could not upload tradebook.",
        });
      }
    } finally {
      setUploading(false);
    }
  }

  const toneClasses = {
    gain: "border-gain/30 bg-gain-soft text-gain",
    loss: "border-loss/30 bg-loss-soft text-loss",
    estimate: "border-estimate/30 bg-estimate-soft text-estimate",
  };

  return (
    <div className="mb-4">
      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" onClick={() => router.push("/brokers")}>
          <LinkIcon />
          Connect or Sync Broker
        </Button>
        <Button variant="secondary" onClick={() => setPanelOpen((v) => !v)}>
          <UploadIcon />
          Upload Tradebook (CSV / Excel)
        </Button>
      </div>

      {panelOpen && (
        <Card className="mt-3 p-5">
          <p className="font-display text-base text-ink">Upload your tradebook</p>
          <p className="mt-1 text-sm text-ink-muted">
            Supports CSV or Excel (.xlsx) files exported from Zerodha, Upstox,
            Groww, or any broker. Trades will be added to your portfolio.
          </p>

          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const dropped = e.dataTransfer.files?.[0];
              if (dropped) setFile(dropped);
            }}
            className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-8 text-center transition-colors ${
              dragOver ? "border-brand bg-brand-soft/40" : "border-rule hover:border-rule-strong"
            }`}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-ink-faint">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M17 8l-5-5-5 5" />
              <path d="M12 3v12" />
            </svg>
            <p className="mt-2 text-sm text-ink-muted">
              {file ? <span className="font-medium text-ink">{file.name}</span> : "Drag and drop, or click to select a file"}
            </p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {message && (
            <div className={`mt-4 rounded-md border px-3 py-2.5 text-sm ${toneClasses[message.tone]}`}>
              {message.text}
            </div>
          )}

          <div className="mt-4 flex items-center gap-3">
            <Button onClick={handleUpload} loading={uploading} disabled={!file}>
              Upload &amp; Process
            </Button>
            <button
              type="button"
              onClick={reset}
              className="cursor-pointer text-sm font-medium text-ink-muted hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
