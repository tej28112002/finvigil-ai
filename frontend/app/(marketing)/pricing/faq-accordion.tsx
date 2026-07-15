"use client";

import { useState } from "react";
import type { FaqItem } from "./pricing-data";

export function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <div className="mx-auto max-w-2xl divide-y divide-rule border-t border-rule">
      {items.map((item, i) => {
        const open = openIndex === i;
        return (
          <div key={item.question}>
            <button
              type="button"
              onClick={() => setOpenIndex(open ? null : i)}
              aria-expanded={open}
              className="flex w-full cursor-pointer items-center justify-between gap-4 py-5 text-left"
            >
              <span className="font-display text-base text-ink">{item.question}</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`shrink-0 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`}
                aria-hidden="true"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
            {open && (
              <p className="pb-5 text-sm leading-relaxed text-ink-muted">{item.answer}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
