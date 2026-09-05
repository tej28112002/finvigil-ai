"use client";

import { useEffect, useState } from "react";
import { BrokerActionsBar } from "@/components/shared/broker-actions-bar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api";

interface PerformanceMetrics {
  net_pnl: number;
  win_rate_pct: number;
  profit_factor: number | null;
  total_trades: number;
  avg_trade_return: number;
}

interface PsychologicalProfile {
  overall_state: string;
  discipline_score: number;
  revenge_trading_detected: boolean;
  revenge_trading_evidence: string | null;
  overtrading_detected: boolean;
  overtrading_evidence: string | null;
  fomo_detected: boolean;
  emotional_state: string;
}

interface TradeBehavior {
  trade_type: string;
  avg_holding_days: number;
  stop_loss_adherence_pct: number | null;
  best_time_observation: string | null;
  worst_time_observation: string | null;
}

interface InstrumentAnalysis {
  instrument: string;
  trades: number;
  win_rate_pct: number;
  avg_pnl: number;
  verdict: string;
}

interface RiskManagement {
  avg_risk_per_trade_pct: number | null;
  max_consecutive_losses: number;
  recovery_behavior: string;
  worst_day_pnl: number;
}

interface AnalysisJson {
  grade: string;
  grade_reason: string;
  performance: PerformanceMetrics;
  psychological_profile: PsychologicalProfile | null;
  trade_behavior: TradeBehavior | null;
  instrument_analysis: InstrumentAnalysis[];
  risk_management: RiskManagement | null;
  actionable_insights: string[];
  one_line_verdict: string;
  analysis_unavailable?: boolean;
}

interface AnalysisMeta {
  week_start: string;
  week_end: string;
  trade_count: number;
}

interface HistoryItem {
  id: string;
  week_start: string;
  week_end: string;
  grade: string;
  trade_count: number;
  analysis_type: string;
  created_at: string;
}

interface ComparisonJson {
  performance_delta: {
    pnl_change_pct: number;
    win_rate_change: number;
    verdict: string;
  } | null;
  psychological_change: {
    discipline_change: string;
    revenge_trading: string;
    overtrading: string;
    summary: string;
  } | null;
  improvements: string[];
  still_needs_work: string[];
  trajectory: string;
  coach_message: string;
  next_week_focus: string;
}

interface LatestAnalysisResponse {
  status?: "no_analysis";
  week_start?: string;
  week_end?: string;
  trade_count?: number;
  analysis?: AnalysisJson;
}

interface RunAnalysisResponse {
  status: "completed" | "insufficient_data";
  message?: string;
  week_start?: string;
  week_end?: string;
  trade_count: number;
  analysis?: AnalysisJson;
}

type Toast = { tone: "gain" | "loss" | "estimate"; text: string };

const toneClasses: Record<Toast["tone"], string> = {
  gain: "border-gain/30 bg-gain-soft text-gain",
  loss: "border-loss/30 bg-loss-soft text-loss",
  estimate: "border-estimate/30 bg-estimate-soft text-estimate",
};

function fmtDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function fmtRupee(n: number): string {
  return n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function gradeClasses(grade: string): string {
  if (grade === "A") return "bg-gain-soft text-gain";
  if (grade === "B+" || grade === "B") return "bg-accent-blue-soft text-accent-blue";
  if (grade === "C+" || grade === "C") return "bg-estimate-soft text-estimate";
  if (grade === "D" || grade === "F") return "bg-loss-soft text-loss";
  return "bg-bg text-ink-muted border border-rule";
}

function disciplineBarColor(score: number): string {
  if (score >= 9) return "bg-gain";
  if (score >= 7) return "bg-accent-blue";
  if (score >= 5) return "bg-estimate";
  return "bg-loss";
}

function StatusRow({
  label,
  detected,
  evidence,
}: {
  label: string;
  detected: boolean;
  evidence: string | null;
}) {
  return (
    <div className="border-t border-rule py-3 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink">{label}</span>
        {detected ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-estimate-soft px-2.5 py-1 text-xs font-medium text-estimate">
            ⚠ Detected
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-gain-soft px-2.5 py-1 text-xs font-medium text-gain">
            ✓ Not detected
          </span>
        )}
      </div>
      {detected && evidence && (
        <p className="mt-2 rounded-md bg-estimate-soft px-3 py-2 text-sm text-estimate">
          {evidence}
        </p>
      )}
    </div>
  );
}

export function JournalClient() {
  const [analysis, setAnalysis] = useState<AnalysisJson | null>(null);
  const [meta, setMeta] = useState<AnalysisMeta | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(true);
  const [running, setRunning] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  const [comparison, setComparison] = useState<ComparisonJson | null>(null);
  const [comparing, setComparing] = useState(false);

  function loadHistory() {
    return apiFetch<HistoryItem[]>("/journal/analysis/history")
      .then((result) => setHistory(result))
      .catch(() => setHistory([]));
  }

  useEffect(() => {
    apiFetch<LatestAnalysisResponse>("/journal/analysis/latest")
      .then((result) => {
        if (!result.analysis || result.status === "no_analysis") {
          setAnalysis(null);
          setMeta(null);
        } else {
          setAnalysis(result.analysis);
          setMeta({
            week_start: result.week_start ?? "",
            week_end: result.week_end ?? "",
            trade_count: result.trade_count ?? 0,
          });
        }
      })
      .catch(() => {
        // Leave existing state as-is; the page still renders the "no
        // analysis" / run-analysis affordance either way.
      })
      .finally(() => setLoadingAnalysis(false));

    loadHistory();
  }, []);

  async function handleRunAnalysis() {
    setRunning(true);
    setToast(null);
    try {
      const result = await apiFetch<RunAnalysisResponse>("/journal/analyze", { method: "POST" });
      if (result.status === "insufficient_data") {
        setToast({
          tone: "estimate",
          text: result.message || "Need at least 2 completed trades to generate analysis.",
        });
      } else if (result.status === "completed" && result.analysis) {
        setAnalysis(result.analysis);
        setMeta({
          week_start: result.week_start ?? "",
          week_end: result.week_end ?? "",
          trade_count: result.trade_count,
        });
        setComparison(null);
        setToast({ tone: "gain", text: "New analysis ready." });
        loadHistory();
      }
    } catch (err) {
      setToast({
        tone: "loss",
        text: err instanceof ApiError ? err.message : "Could not run analysis.",
      });
    } finally {
      setRunning(false);
    }
  }

  async function handleCompare() {
    setComparing(true);
    try {
      const result = await apiFetch<{ comparison: ComparisonJson }>("/journal/compare", {
        method: "POST",
      });
      setComparison(result.comparison);
    } catch (err) {
      setToast({
        tone: "loss",
        text: err instanceof ApiError ? err.message : "Could not run comparison.",
      });
    } finally {
      setComparing(false);
    }
  }

  async function handleLoadHistoryItem(item: HistoryItem) {
    try {
      const result = await apiFetch<AnalysisJson>(`/journal/analysis/${item.id}`);
      setAnalysis(result);
      setMeta({
        week_start: item.week_start,
        week_end: item.week_end,
        trade_count: item.trade_count,
      });
      setComparison(null);
    } catch (err) {
      setToast({
        tone: "loss",
        text: err instanceof ApiError ? err.message : "Could not load that analysis.",
      });
    }
  }

  const p = analysis?.performance;
  const trajectoryClasses =
    comparison?.trajectory === "Improving"
      ? "bg-gain-soft text-gain"
      : comparison?.trajectory === "Declining"
        ? "bg-loss-soft text-loss"
        : "bg-bg text-ink-muted border border-rule";
  const trajectoryLabel =
    comparison?.trajectory === "Improving"
      ? "📈 Improving"
      : comparison?.trajectory === "Declining"
        ? "📉 Declining"
        : "➡ Stable";

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-5">
        <h1 className="font-display text-2xl text-ink">AI Journaling</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your trading performance, automatically computed from your trade history.
        </p>
      </div>

      <BrokerActionsBar />

      <div className="mb-5 flex flex-col items-center gap-3">
        <Button onClick={handleRunAnalysis} loading={running} className="w-full sm:w-auto">
          🔍 Run New Analysis
        </Button>
        {running && (
          <p className="text-xs text-ink-muted">
            This can take up to 30 seconds — analyzing your trade history…
          </p>
        )}
        {toast && (
          <div className={`w-full rounded-md border px-3 py-2.5 text-center text-sm ${toneClasses[toast.tone]}`}>
            {toast.text}
          </div>
        )}
      </div>

      {loadingAnalysis ? (
        <div className="space-y-3">
          <div className="h-24 animate-pulse rounded-md bg-surface" />
          <div className="h-20 animate-pulse rounded-md bg-surface" />
        </div>
      ) : !analysis ? (
        <Card className="p-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-brand">
            ℹ
          </div>
          <p className="text-sm text-ink-muted">
            Connect your broker or upload a tradebook, then click Run New Analysis to
            get your AI-powered trade report.
          </p>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Grade header */}
          <Card className="p-6 text-center">
            <div
              className={`mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-full text-[48px] font-display ${gradeClasses(analysis.grade)}`}
            >
              {analysis.grade}
            </div>
            <p className="text-sm text-ink">{analysis.grade_reason}</p>
            <p className="mt-2 text-sm italic text-ink-muted">{analysis.one_line_verdict}</p>
            {meta && (
              <p className="mt-3 text-xs text-ink-faint">
                Period: {fmtDate(meta.week_start)} to {fmtDate(meta.week_end)} ·{" "}
                {meta.trade_count} trades analysed
              </p>
            )}
          </Card>

          {/* Performance cards */}
          {p && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Net P&amp;L</p>
                <p className={`mt-1 font-display text-lg ${p.net_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                  ₹{fmtRupee(p.net_pnl)}
                </p>
              </Card>
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Win Rate</p>
                <p className="mt-1 font-display text-lg text-ink">{p.win_rate_pct.toFixed(1)}%</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Profit Factor</p>
                <p className="mt-1 font-display text-lg text-ink">
                  {p.profit_factor != null ? p.profit_factor.toFixed(2) : "—"}
                </p>
              </Card>
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Avg Trade Return</p>
                <p className={`mt-1 font-display text-lg ${p.avg_trade_return >= 0 ? "text-gain" : "text-loss"}`}>
                  ₹{fmtRupee(p.avg_trade_return)}
                </p>
              </Card>
            </div>
          )}

          {/* Psychological profile */}
          {analysis.psychological_profile && (
            <Card className="p-5">
              <h2 className="font-display text-base text-ink">Psychological Profile</h2>
              <div className="mt-2">
                <StatusRow
                  label="Revenge Trading"
                  detected={analysis.psychological_profile.revenge_trading_detected}
                  evidence={analysis.psychological_profile.revenge_trading_evidence}
                />
                <StatusRow
                  label="Overtrading"
                  detected={analysis.psychological_profile.overtrading_detected}
                  evidence={analysis.psychological_profile.overtrading_evidence}
                />
                <StatusRow
                  label="FOMO"
                  detected={analysis.psychological_profile.fomo_detected}
                  evidence={null}
                />
                <div className="border-t border-rule py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink">Discipline Score</span>
                    <span className="text-sm text-ink-muted">
                      {analysis.psychological_profile.discipline_score}/10
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-bg">
                    <div
                      className={`h-1.5 rounded-full ${disciplineBarColor(analysis.psychological_profile.discipline_score)}`}
                      style={{ width: `${analysis.psychological_profile.discipline_score * 10}%` }}
                    />
                  </div>
                </div>
              </div>
              <p className="mt-3 text-sm italic text-ink-muted">
                {analysis.psychological_profile.emotional_state}
              </p>
            </Card>
          )}

          {/* Actionable insights */}
          {analysis.actionable_insights?.length > 0 && (
            <div>
              <h2 className="mb-2 font-display text-base text-ink">What to do next week</h2>
              <div className="space-y-2">
                {analysis.actionable_insights.map((insight, i) => (
                  <Card key={i} className="flex items-start gap-3 p-4">
                    <span className="text-brand">→</span>
                    <span className="text-sm text-ink">
                      {i + 1}. {insight}
                    </span>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Instrument breakdown */}
          {analysis.instrument_analysis?.length > 0 && (
            <div>
              <h2 className="mb-2 font-display text-base text-ink">By Instrument</h2>
              <Card className="overflow-x-auto p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-rule text-left text-xs uppercase tracking-wider text-ink-muted">
                      <th className="px-4 py-2.5">Instrument</th>
                      <th className="px-4 py-2.5">Trades</th>
                      <th className="px-4 py-2.5">Win Rate</th>
                      <th className="px-4 py-2.5">Avg P&amp;L</th>
                      <th className="px-4 py-2.5">Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.instrument_analysis.map((row, i) => (
                      <tr key={i} className="border-b border-rule last:border-b-0">
                        <td className="px-4 py-2.5 text-ink">{row.instrument}</td>
                        <td className="px-4 py-2.5 text-ink-muted">{row.trades}</td>
                        <td className="px-4 py-2.5 text-ink-muted">{row.win_rate_pct.toFixed(1)}%</td>
                        <td className={`px-4 py-2.5 ${row.avg_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                          ₹{fmtRupee(row.avg_pnl)}
                        </td>
                        <td className={`px-4 py-2.5 ${row.avg_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                          {row.verdict}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {/* Compare button */}
          {history.length >= 2 && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleCompare} loading={comparing}>
                📊 Compare with previous period →
              </Button>
            </div>
          )}

          {/* Comparison result */}
          {comparison && (
            <Card className="p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-base text-ink">Comparison Result</h2>
                <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${trajectoryClasses}`}>
                  {trajectoryLabel}
                </span>
              </div>

              <div className="mt-3 rounded-md bg-brand-soft px-4 py-3 text-sm text-ink">
                {comparison.coach_message}
              </div>

              {comparison.improvements?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Improvements</p>
                  <ul className="mt-1.5 space-y-1">
                    {comparison.improvements.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gain">
                        <span>✓</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {comparison.still_needs_work?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium uppercase tracking-wider text-ink-muted">Still Needs Work</p>
                  <ul className="mt-1.5 space-y-1">
                    {comparison.still_needs_work.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-estimate">
                        <span>⚠</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-4 rounded-md border border-rule px-4 py-3 text-sm">
                <span className="font-medium text-ink">Focus next week: </span>
                <span className="text-ink-muted">{comparison.next_week_focus}</span>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Analysis history */}
      {history.length > 0 && (
        <div className="mt-6">
          <button
            type="button"
            onClick={() => setHistoryOpen((v) => !v)}
            className="cursor-pointer text-sm font-medium text-ink-muted hover:text-ink"
          >
            View past analyses {historyOpen ? "▴" : "▾"}
          </button>
          {historyOpen && (
            <div className="mt-3 space-y-2">
              {history.map((item) => (
                <Card
                  key={item.id}
                  interactive
                  className="flex cursor-pointer items-center justify-between p-3"
                >
                  <button
                    type="button"
                    onClick={() => handleLoadHistoryItem(item)}
                    className="flex w-full cursor-pointer items-center justify-between text-left"
                  >
                    <span className="text-sm text-ink">
                      {fmtDate(item.week_start)} – {fmtDate(item.week_end)}
                      <span className="ml-2 text-ink-muted">
                        ({item.trade_count} trades{item.analysis_type === "comparison" ? ", comparison" : ""})
                      </span>
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${gradeClasses(item.grade)}`}>
                      {item.grade}
                    </span>
                  </button>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
