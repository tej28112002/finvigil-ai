"use client";

import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, MetricLabel } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetch, ApiError } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

// ── types ────────────────────────────────────────────────────────────────────

interface JournalTag {
  id: string;
  tag_name: string;
}

interface JournalEntry {
  id: string;
  transcript: string;
  created_at: string;
}

interface JournalEntryWithTags {
  entry: JournalEntry;
  tags: JournalTag[];
}

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const inputCls =
  "h-9 w-full rounded-md border border-rule bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/40";

// apiFetch always parses JSON; audio upload needs FormData + a raw
// multipart POST, so this bypasses apiFetch the same way ca-bundle-button
// does for its binary download.
async function uploadAudio(blob: Blob): Promise<JournalEntryWithTags> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    window.location.href = "/login";
    throw new Error("No active session");
  }

  const formData = new FormData();
  formData.append("file", blob, "recording.webm");

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/journal/entries/audio`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: formData,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

// ── main component ────────────────────────────────────────────────────────────

export function JournalClient() {
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [entries, setEntries] = useState<JournalEntryWithTags[] | null>(null);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [micUnsupported, setMicUnsupported] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [textInput, setTextInput] = useState("");
  const [submittingText, setSubmittingText] = useState(false);

  const [pendingEntry, setPendingEntry] = useState<JournalEntryWithTags | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [savingTags, setSavingTags] = useState(false);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function loadEntries() {
    setLoadingEntries(true);
    try {
      const data = await apiFetch<JournalEntryWithTags[]>("/journal/entries");
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load journal entries.");
    } finally {
      setLoadingEntries(false);
    }
  }

  useEffect(() => {
    apiFetch<{ tags: Record<string, string> }>("/journal/tags/taxonomy")
      .then((r) => setTaxonomy(r.tags))
      .catch(() => setTaxonomy({}));
    loadEntries();
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setMicUnsupported(true);
    }
  }, []);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setTranscribing(true);
        try {
          const result = await uploadAudio(blob);
          setPendingEntry(result);
          setSelectedTags([]);
          await loadEntries();
        } catch (err) {
          if (err instanceof ApiError && err.status === 503) {
            setError(
              "Voice transcription isn't configured yet on the server — try typing your entry below instead."
            );
          } else {
            setError(err instanceof Error ? err.message : "Transcription failed.");
          }
        } finally {
          setTranscribing(false);
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Microphone access was denied or unavailable.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  async function handleTextSubmit() {
    if (!textInput.trim()) {
      setError("Write something before submitting.");
      return;
    }
    setError(null);
    setSubmittingText(true);
    try {
      const result = await apiFetch<JournalEntryWithTags>("/journal/entries/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: textInput }),
      });
      setPendingEntry(result);
      setSelectedTags([]);
      setTextInput("");
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save entry.");
    } finally {
      setSubmittingText(false);
    }
  }

  function toggleTag(tag: string) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function handleSaveTags() {
    if (!pendingEntry || selectedTags.length === 0) {
      setPendingEntry(null);
      return;
    }
    setSavingTags(true);
    try {
      await apiFetch(`/journal/entries/${pendingEntry.entry.id}/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tag_names: selectedTags }),
      });
      setPendingEntry(null);
      setSelectedTags([]);
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save tags.");
    } finally {
      setSavingTags(false);
    }
  }

  async function handleDelete(entryId: string) {
    setDeletingId(entryId);
    try {
      await apiFetch(`/journal/entries/${entryId}`, { method: "DELETE" });
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete entry.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">Trading Journal</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Record how you felt about a trade — reflection, not advice. Raw audio is
          transcribed and discarded immediately; only the text is kept.
        </p>
      </div>

      {/* ── Record / write entry ── */}
      <Card className="p-5">
        <h2 className="mb-4 font-display text-base text-ink">New entry</h2>

        {!micUnsupported && (
          <div className="flex items-center gap-3">
            {!recording ? (
              <Button onClick={startRecording} disabled={transcribing}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <circle cx="12" cy="12" r="8" />
                </svg>
                Record
              </Button>
            ) : (
              <Button onClick={stopRecording} variant="secondary">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
                Stop &amp; transcribe
              </Button>
            )}
            {recording && (
              <Badge tone="loss">
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-loss" />
                  Recording
                </span>
              </Badge>
            )}
            {transcribing && <Badge tone="estimate">Transcribing…</Badge>}
          </div>
        )}

        <div className="mt-4 flex items-start gap-2">
          <textarea
            className={`${inputCls} h-20 resize-none`}
            placeholder="…or just type how you're feeling about a trade"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
          />
        </div>
        <div className="mt-2 flex justify-end">
          <Button
            variant="secondary"
            onClick={handleTextSubmit}
            loading={submittingText}
            className="h-8 px-3 text-xs"
          >
            Save entry
          </Button>
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-loss/30 bg-loss-soft px-4 py-2.5 text-sm text-loss">
            {error}
          </div>
        )}
      </Card>

      {/* ── Tag the entry just created ── */}
      {pendingEntry && (
        <Card className="mt-4 p-5">
          <MetricLabel>Tag this entry (optional)</MetricLabel>
          <p className="mt-2 text-sm text-ink-muted italic">&ldquo;{pendingEntry.entry.transcript}&rdquo;</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(taxonomy).map(([tag, description]) => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                title={description}
                className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  selectedTags.includes(tag)
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-rule text-ink-muted hover:text-ink"
                }`}
              >
                {tag.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setPendingEntry(null)} className="h-8 px-3 text-xs">
              Skip
            </Button>
            <Button onClick={handleSaveTags} loading={savingTags} className="h-8 px-3 text-xs">
              Save tags
            </Button>
          </div>
        </Card>
      )}

      {/* ── Entries list ── */}
      <div className="mt-6">
        <h2 className="mb-3 font-display text-lg text-ink">Past entries</h2>
        {loadingEntries ? (
          <p className="text-sm text-ink-faint">Loading…</p>
        ) : !entries || entries.length === 0 ? (
          <EmptyState
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="9" y="2" width="6" height="12" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <path d="M12 19v3" />
              </svg>
            }
            title="No journal entries yet"
            description="Record a voice note or type a quick reflection above to get started."
          />
        ) : (
          <div className="space-y-3">
            {entries.map(({ entry, tags }) => (
              <Card key={entry.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-ink">{entry.transcript}</p>
                    {tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {tags.map((t) => (
                          <Badge key={t.id} tone="brand">
                            {t.tag_name.replace(/_/g, " ")}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <p className="mt-2 text-xs text-ink-faint">{fmtDate(entry.created_at)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(entry.id)}
                    disabled={deletingId === entry.id}
                    className="shrink-0 cursor-pointer rounded p-1 text-ink-faint transition-colors hover:text-loss disabled:opacity-50"
                    aria-label="Delete entry"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6h16Z" />
                    </svg>
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Card className="mt-6 p-4">
        <p className="flex items-start gap-2 text-xs text-ink-muted">
          <Badge tone="estimate">Not financial advice</Badge>
          <span>
            This journal is for personal reflection only — it never suggests buy or
            sell decisions. Raw voice recordings are deleted immediately after
            transcription; only the text is kept. Delete any entry at any time.
          </span>
        </p>
      </Card>
    </div>
  );
}
