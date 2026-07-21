import { useEffect, useMemo, useRef, useState } from "react";
import { displayKet, generateBasisStates, normalizeBasisState } from "../../utils/basisState";

const MAX_RENDERED_OPTIONS = 64;

interface BasisStateSelectionModalProps {
  numQubits: number;
  initialBasisState?: string;
  onCancel: () => void;
  onConfirm: (basisState: string) => void;
}

export function BasisStateSelectionModal({
  numQubits,
  initialBasisState,
  onCancel,
  onConfirm,
}: BasisStateSelectionModalProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(() => normalizeBasisState(numQubits, initialBasisState));
  const [activeIndex, setActiveIndex] = useState(0);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const options = useMemo(() => generateBasisStates(numQubits), [numQubits]);
  const filtered = useMemo(() => {
    const trimmed = query.trim().replace(/[|>\u27e9\s]/g, "");
    if (!trimmed) return options;
    return options.filter((option) => option.includes(trimmed));
  }, [options, query]);
  const visible = filtered.slice(0, options.length > MAX_RENDERED_OPTIONS ? MAX_RENDERED_OPTIONS : filtered.length);
  const totalStates = 1 << numQubits;

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, Math.max(0, visible.length - 1)));
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((index) => Math.max(0, index - 1));
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        const active = visible[activeIndex] ?? selected;
        onConfirm(active);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, onCancel, onConfirm, selected, visible]);

  const chooseRandom = () => {
    const random = options[Math.floor(Math.random() * options.length)] ?? "0".repeat(numQubits);
    setSelected(random);
    setQuery(random);
  };

  const reset = () => {
    const zero = "0".repeat(numQubits);
    setSelected(zero);
    setQuery("");
  };

  return (
    <div className="basis-modal" role="dialog" aria-modal="true" aria-labelledby="basis-modal-title">
      <div className="basis-modal-panel">
        <div className="basis-modal-header">
          <div>
            <h2 id="basis-modal-title">Select Initial Computational Basis State</h2>
            <p>{numQubits} qubits, {totalStates} basis states</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} aria-label="Close basis selector">
            X
          </button>
        </div>

        <div className="basis-modal-tools">
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Search ${displayKet("0".repeat(numQubits))}`}
            className="basis-search"
          />
          <button type="button" className="btn btn-secondary btn-sm" onClick={chooseRandom}>
            Random Basis State
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={reset}>
            Reset to {displayKet("0".repeat(numQubits))}
          </button>
        </div>

        <div className="basis-selected">
          <span>Selected</span>
          <strong>{displayKet(selected)}</strong>
        </div>

        <div className="basis-options" role="listbox" aria-label="Computational basis states">
          {visible.map((option, index) => (
            <button
              key={option}
              type="button"
              role="option"
              aria-selected={selected === option}
              className={`basis-option ${selected === option ? "is-selected" : ""} ${activeIndex === index ? "is-active" : ""}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => setSelected(option)}
              onDoubleClick={() => onConfirm(option)}
            >
              <span>{displayKet(option)}</span>
              <small>index {Number.parseInt(option, 2)}</small>
            </button>
          ))}
          {filtered.length === 0 && <div className="basis-empty">No matching basis states.</div>}
        </div>

        {options.length > MAX_RENDERED_OPTIONS && filtered.length > visible.length && (
          <p className="basis-hint">
            Showing {visible.length} of {filtered.length} matches. Keep typing to narrow the dropdown.
          </p>
        )}

        <div className="basis-modal-actions">
          <button type="button" className="btn btn-ghost btn-md" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-md" onClick={() => onConfirm(selected)}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
