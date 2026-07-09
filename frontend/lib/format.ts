/**
 * Money formatting & exact decimal arithmetic.
 *
 * BRD rule: all money display honors backend Decimal strings — no float math
 * on money in JS, format only. The backend serializes Postgres NUMERIC(18,8)
 * as strings like "110000.00000000" and "0E-8" (scientific notation for
 * zero at scale 8), so parsing must handle exponent forms WITHOUT going
 * through Number(). Everything here is string/BigInt only.
 */

const DECIMAL_RE = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/;

/** Parse a backend decimal string into exact paise (scale 2), round-half-up. */
export function parseDecimalToPaise(value: string): bigint {
  const match = DECIMAL_RE.exec(value.trim());
  if (!match) {
    throw new Error(`Not a decimal string: "${value}"`);
  }
  const [, sign, intPart, fracPart = "", expPart = "0"] = match;

  const digits = intPart + fracPart;
  // value = digits × 10^effExp; paise = value × 100 = digits × 10^(effExp + 2)
  const shift = parseInt(expPart, 10) - fracPart.length + 2;

  let paise: bigint;
  if (shift >= 0) {
    paise = BigInt(digits) * 10n ** BigInt(shift);
  } else {
    const keep = digits.length + shift; // drop -shift trailing digits
    if (keep <= 0) {
      const firstDropped = keep === 0 ? digits[0] : "0";
      paise = firstDropped >= "5" ? 1n : 0n;
    } else {
      paise = BigInt(digits.slice(0, keep));
      if (digits[keep] >= "5") paise += 1n;
    }
  }
  return sign === "-" ? -paise : paise;
}

/** Exact sum of backend decimal strings, returned as paise. */
export function sumToPaise(values: string[]): bigint {
  return values.reduce((acc, v) => acc + parseDecimalToPaise(v), 0n);
}

export interface INRParts {
  sign: "" | "-" | "+";
  symbol: "₹";
  integer: string; // Indian-grouped: "1,10,000"
  fraction: string; // always 2 digits: "00"
}

/** Indian digit grouping: last 3 digits, then groups of 2 (1,23,45,678). */
function groupIndian(intDigits: string): string {
  if (intDigits.length <= 3) return intDigits;
  const last3 = intDigits.slice(-3);
  let rest = intDigits.slice(0, -3);
  const groups: string[] = [];
  while (rest.length > 2) {
    groups.unshift(rest.slice(-2));
    rest = rest.slice(0, -2);
  }
  groups.unshift(rest);
  return `${groups.join(",")},${last3}`;
}

export function formatINRParts(
  value: string | bigint,
  opts: { signed?: boolean } = {}
): INRParts {
  const paise = typeof value === "bigint" ? value : parseDecimalToPaise(value);
  const negative = paise < 0n;
  const abs = negative ? -paise : paise;
  const whole = abs / 100n;
  const frac = abs % 100n;
  return {
    sign: negative ? "-" : opts.signed && paise > 0n ? "+" : "",
    symbol: "₹",
    integer: groupIndian(whole.toString()),
    fraction: frac.toString().padStart(2, "0"),
  };
}

/** "₹1,10,000.00" — convenience string form. */
export function formatINR(
  value: string | bigint,
  opts: { signed?: boolean } = {}
): string {
  const p = formatINRParts(value, opts);
  return `${p.sign}${p.symbol}${p.integer}.${p.fraction}`;
}

/** Sign of a backend decimal string without float conversion. */
export function decimalSign(value: string): -1 | 0 | 1 {
  const paise = parseDecimalToPaise(value);
  return paise === 0n ? 0 : paise < 0n ? -1 : 1;
}
