"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = useState<"loading" | "authorized" | "denied">("loading");

  useEffect(() => {
    apiFetch<{ role: string }>("/me")
      .then((me) => setState(me.role === "admin" ? "authorized" : "denied"))
      .catch(() => setState("denied"));
  }, []);

  if (state === "loading") return null;

  if (state === "denied") {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="font-display text-xl text-ink">Not authorized</p>
        <p className="mt-2 text-sm text-ink-muted">
          You don&apos;t have permission to access this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
