/**
 * The last seven days as seven paw prints. A filled print means the person checked in
 * that day; an outlined one means they did not, which is fine. Not a streak and not a
 * score: nothing counts up, nothing is lost.
 */
export function PawWeek({ lit, label }: { lit: readonly boolean[]; label: string }) {
  return (
    <div role="img" aria-label={label} data-week className="grid grid-cols-7 gap-1 px-2 py-6">
      {lit.map((on, index) => (
        <svg
          key={index}
          viewBox="0 0 40 40"
          aria-hidden="true"
          data-lit={on || undefined}
          className={`mx-auto w-9 sm:w-11 ${on ? "text-[#f472b6]" : "text-dim opacity-60"} ${
            index % 2 ? "translate-y-2" : ""
          }`}
        >
          <g fill={on ? "currentColor" : "none"} stroke="currentColor" strokeWidth={on ? 0 : 1.6}>
            <ellipse cx="20" cy="27" rx="9" ry="7.5" />
            <ellipse cx="9" cy="16" rx="3.6" ry="4.6" />
            <ellipse cx="16" cy="10" rx="3.6" ry="4.8" />
            <ellipse cx="24" cy="10" rx="3.6" ry="4.8" />
            <ellipse cx="31" cy="16" rx="3.6" ry="4.6" />
          </g>
        </svg>
      ))}
    </div>
  );
}
