/**
 * Shown instantly by Next.js Suspense while a route compiles or streams.
 * Eliminates the blank-page flash on first navigation to any (app)/ route.
 */
export default function AppLoading() {
  return (
    <div className="mx-auto max-w-5xl animate-pulse space-y-5">
      {/* Page title */}
      <div className="h-6 w-40 rounded-md bg-rule" />

      {/* Metric card row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border border-rule bg-surface p-5">
            <div className="h-3 w-24 rounded bg-rule" />
            <div className="mt-4 h-8 w-32 rounded bg-rule" />
            <div className="mt-2 h-3 w-20 rounded bg-rule" />
          </div>
        ))}
      </div>

      {/* Content card */}
      <div className="rounded-lg border border-rule bg-surface p-5">
        <div className="h-4 w-36 rounded bg-rule" />
        <div className="mt-5 space-y-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-4">
              <div className="h-4 flex-1 rounded bg-rule" />
              <div className="h-4 w-24 rounded bg-rule" />
              <div className="h-4 w-20 rounded bg-rule" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
