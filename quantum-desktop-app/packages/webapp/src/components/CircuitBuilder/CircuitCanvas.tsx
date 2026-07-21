import { useMemo, useState } from "react";
import {
  useDndContext,
  useDraggable,
  useDroppable,
} from "@dnd-kit/core";
import { useCircuitStore, MAX_QUBITS_CONST } from "../../store/circuitStore";
import {
  gateMeta,
  type GatePlacement,
  type GateType,
} from "../../types";
import { displayKet, generateBasisStates } from "../../utils/basisState";
import { BasisStateSelectionModal } from "./BasisStateSelectionModal";
import { ThetaInput, formatTheta } from "./ThetaControls";

const WIRE_LEFT_PAD = 64;
const COLUMN_WIDTH = 88;
const ROW_HEIGHT = 64;
const MAX_VISIBLE_COLUMNS = 14;

export function CircuitCanvas(): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const gates = useCircuitStore((s) => s.gates);
  const isRunning = useCircuitStore((s) => s.isRunning);
  const stepMode = useCircuitStore((s) => s.stepMode);
  const currentStep = useCircuitStore((s) => s.currentStep);
  const selectedBasisState = useCircuitStore((s) => s.selectedBasisState);
  const addQubitWithBasisState = useCircuitStore((s) => s.addQubitWithBasisState);
  const removeQubit = useCircuitStore((s) => s.removeQubit);
  const [basisModalOpen, setBasisModalOpen] = useState(false);
  const [initialStateModalOpen, setInitialStateModalOpen] = useState(false);

  const usedColumns = useMemo(() => {
    const maxStep = gates.reduce((m, g) => Math.max(m, g.timeStep), -1);
    return Math.max(maxStep + 2, 6);
  }, [gates]);

  const totalColumns = Math.min(MAX_VISIBLE_COLUMNS, Math.max(usedColumns, 6));

  return (
    <div className="circuit-canvas-shell px-4 pb-3 pt-3">
      <div
        className={`relative flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-bg-surface/40 ${
          isRunning ? "animate-neon-border" : ""
        }`}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-border/60 px-4 py-2.5">
          <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Circuit Canvas
          </h2>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <InitialStateControl onOpenSearch={() => setInitialStateModalOpen(true)} />
            <button
              type="button"
              onClick={removeQubit}
              disabled={numQubits <= 1}
              className="rounded border border-border px-2 py-0.5 font-mono text-[10px] text-text-secondary hover:border-red-500/40 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-30"
            >
              − Qubit
            </button>
            <button
              type="button"
              onClick={() => setBasisModalOpen(true)}
              disabled={numQubits >= MAX_QUBITS_CONST}
              className="rounded border border-accent-quantum/40 bg-accent-quantum/10 px-2 py-0.5 font-mono text-[10px] text-accent-glow hover:bg-accent-quantum/20 disabled:cursor-not-allowed disabled:opacity-30"
            >
              + Qubit
            </button>
          </div>
        </div>
        <div className="circuit-canvas-viewport px-4 py-3">
          <div
            className="relative"
            style={{
              width: WIRE_LEFT_PAD + totalColumns * COLUMN_WIDTH + 8,
              minHeight: numQubits * ROW_HEIGHT,
            }}
          >
            {Array.from({ length: numQubits }).map((_, q) => (
              <QubitRow
                key={q}
                qubit={q}
                totalColumns={totalColumns}
                gates={gates}
                isRunning={isRunning}
                stepMode={stepMode}
                currentStep={currentStep}
                numQubits={numQubits}
              />
            ))}
            <CnotConnectors gates={gates} />
          </div>
        </div>
      </div>
      {basisModalOpen && (
        <BasisStateSelectionModal
          numQubits={numQubits + 1}
          initialBasisState={`${selectedBasisState}0`}
          onCancel={() => setBasisModalOpen(false)}
          onConfirm={(basisState) => {
            addQubitWithBasisState(basisState);
            setBasisModalOpen(false);
          }}
        />
      )}
      {initialStateModalOpen && (
        <BasisStateSelectionModal
          numQubits={numQubits}
          initialBasisState={selectedBasisState}
          onCancel={() => setInitialStateModalOpen(false)}
          onConfirm={(basisState) => {
            useCircuitStore.getState().setInitialBasisState(basisState);
            setInitialStateModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

function InitialStateControl({ onOpenSearch }: { onOpenSearch: () => void }): JSX.Element {
  const numQubits = useCircuitStore((s) => s.numQubits);
  const selectedBasisState = useCircuitStore((s) => s.selectedBasisState);
  const setInitialBasisState = useCircuitStore((s) => s.setInitialBasisState);
  const resetInitialBasisState = useCircuitStore((s) => s.resetInitialBasisState);
  const randomizeInitialBasisState = useCircuitStore((s) => s.randomizeInitialBasisState);
  const options = useMemo(() => generateBasisStates(numQubits), [numQubits]);
  const zeroKet = displayKet("0".repeat(numQubits));

  return (
    <div className="initial-state-control">
      <label htmlFor="initial-state-select">Initial State</label>
      {options.length <= 64 ? (
        <select
          id="initial-state-select"
          value={selectedBasisState}
          onChange={(event) => setInitialBasisState(event.target.value)}
          aria-label="Initial computational basis state"
        >
          {options.map((option) => (
            <option key={option} value={option}>
              {displayKet(option)}
            </option>
          ))}
        </select>
      ) : (
        <button
          type="button"
          className="initial-state-select-button"
          onClick={onOpenSearch}
          aria-label="Open searchable initial state dropdown"
        >
          <span>{displayKet(selectedBasisState)}</span>
          <span aria-hidden="true">v</span>
        </button>
      )}
      <button type="button" className="initial-state-mini" onClick={resetInitialBasisState}>
        Reset to {zeroKet}
      </button>
      <button type="button" className="initial-state-mini" onClick={randomizeInitialBasisState}>
        Random Basis State
      </button>
    </div>
  );
}

function QubitRow({
  qubit,
  totalColumns,
  gates,
  isRunning,
  stepMode,
  currentStep,
  numQubits,
}: {
  qubit: number;
  totalColumns: number;
  gates: GatePlacement[];
  isRunning: boolean;
  stepMode: boolean;
  currentStep: number;
  numQubits: number;
}): JSX.Element {
  return (
    <div
      className="relative"
      style={{ height: ROW_HEIGHT }}
      data-qubit-row={qubit}
    >
      <div
        className="absolute left-0 top-1/2 -translate-y-1/2 font-mono text-[11px] text-text-secondary"
        style={{ width: WIRE_LEFT_PAD - 8 }}
      >
        <span className="block">q[{qubit}]</span>
        <span className="text-[9px] text-text-muted">{displayKet("0")}</span>
      </div>
      <div
        className="absolute top-1/2 -translate-y-1/2 overflow-hidden rounded-full bg-gradient-to-r from-accent-quantum/20 via-text-muted/40 to-text-muted/40"
        style={{
          left: WIRE_LEFT_PAD,
          width: totalColumns * COLUMN_WIDTH,
          height: 2,
        }}
      >
        {isRunning && <div className="wire-pulse animate-wire-pulse" />}
      </div>
      <div className="absolute inset-0 flex" style={{ paddingLeft: WIRE_LEFT_PAD }}>
        {Array.from({ length: totalColumns }).map((_, c) => (
          <DropCell key={c} qubit={qubit} timeStep={c} numQubits={numQubits} />
        ))}
      </div>
      {gates
        .filter((g) => g.qubitTargets[0] === qubit && g.qubitTargets.length === 1)
        .map((g) => (
          <PlacedGate
            key={g.id}
            placement={g}
            stepMode={stepMode}
            currentStep={currentStep}
            stepOrder={getStepOrder(gates, g.id)}
          />
        ))}
      {gates
        .filter((g) => g.qubitTargets.length === 2 && g.qubitTargets[0] === qubit)
        .map((g) => (
          <CnotControlChip
            key={`${g.id}-control`}
            placement={g}
            stepMode={stepMode}
            currentStep={currentStep}
            stepOrder={getStepOrder(gates, g.id)}
          />
        ))}
      {gates
        .filter((g) => g.qubitTargets.length === 2 && g.qubitTargets[1] === qubit)
        .map((g) => (
          <CnotTargetChip
            key={`${g.id}-target`}
            placement={g}
            stepMode={stepMode}
            currentStep={currentStep}
            stepOrder={getStepOrder(gates, g.id)}
          />
        ))}
    </div>
  );
}

function getStepOrder(gates: GatePlacement[], id: string): number {
  const ordered = [...gates].sort((a, b) => a.timeStep - b.timeStep || a.id.localeCompare(b.id));
  return ordered.findIndex((g) => g.id === id);
}

function DropCell({
  qubit,
  timeStep,
  numQubits,
}: {
  qubit: number;
  timeStep: number;
  numQubits: number;
}): JSX.Element {
  const { active } = useDndContext();
  const activeData = active?.data?.current as
    | { arity?: 1 | 2; gateType?: GateType }
    | undefined;
  const disabled =
    activeData?.arity === 2 && qubit + 1 >= numQubits;
  const { setNodeRef, isOver } = useDroppable({
    id: `cell-${qubit}-${timeStep}`,
    data: { type: "cell", qubit, timeStep },
    disabled,
  });
  const showHighlight = isOver && active != null && !disabled;
  const showReject = isOver && active != null && disabled;
  return (
    <div
      ref={setNodeRef}
      style={{ width: COLUMN_WIDTH, height: "100%" }}
      className={`relative flex-shrink-0 transition-colors ${
        showHighlight
          ? "bg-accent-quantum/15 outline outline-1 outline-accent-quantum/60"
          : showReject
            ? "bg-red-500/10 outline outline-1 outline-red-500/40"
            : ""
      }`}
    />
  );
}

function PlacedGate({
  placement,
  stepMode,
  currentStep,
  stepOrder,
}: {
  placement: GatePlacement;
  stepMode: boolean;
  currentStep: number;
  stepOrder: number;
}): JSX.Element {
  const meta = gateMeta(placement.gateType);
  const removeGate = useCircuitStore((s) => s.removeGate);
  const updateGateParams = useCircuitStore((s) => s.updateGateParams);
  const [editing, setEditing] = useState(false);
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `placement-${placement.id}`,
    data: {
      source: "placement",
      placementId: placement.id,
      gateType: placement.gateType,
      takesTheta: meta.takesTheta,
      arity: meta.arity,
    },
  });
  const left = WIRE_LEFT_PAD + placement.timeStep * COLUMN_WIDTH + COLUMN_WIDTH / 2 - 28;
  const dimmed = stepMode && stepOrder >= currentStep;
  const labelMain = placement.gateType;
  return (
    <div
      className={`group absolute top-1/2 z-10 -translate-y-1/2 ${dimmed ? "opacity-30" : "opacity-100"} ${
        isDragging ? "opacity-30" : ""
      }`}
      style={{ left }}
    >
      <button
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        type="button"
        onClick={(e) => {
          // Only treat as click when no drag occurred (PointerSensor activation
          // distance gates real drags; click events still fire on plain taps).
          if (meta.takesTheta) {
            e.preventDefault();
            setEditing((s) => !s);
          }
        }}
        className="gate-chip flex cursor-grab flex-col items-center justify-center rounded-md border-2 bg-bg-surface px-2 py-1 shadow-md transition hover:scale-[1.04] active:cursor-grabbing"
        style={{
          borderColor: meta.color,
          minWidth: 56,
          boxShadow: `0 0 0 1px ${meta.color}55, 0 0 12px ${meta.color}22`,
          touchAction: "none",
        }}
      >
        <span className="font-display text-sm font-semibold" style={{ color: meta.color }}>
          {labelMain}
        </span>
        {meta.takesTheta && placement.params.theta !== undefined && (
          <span className="font-mono text-[9px] text-text-secondary">
            θ={formatTheta(placement.params.theta)}
          </span>
        )}
      </button>
      <button
        type="button"
        onClick={() => removeGate(placement.id)}
        className="absolute -right-2 -top-2 hidden h-4 w-4 items-center justify-center rounded-full bg-bg-base text-[9px] text-text-secondary ring-1 ring-border hover:bg-red-500/20 hover:text-red-300 group-hover:flex"
        aria-label="remove gate"
      >
        ×
      </button>
      {editing && meta.takesTheta && (
        <div className="absolute left-1/2 top-full z-20 mt-2 -translate-x-1/2 rounded-md border border-border bg-bg-surface p-3 shadow-xl">
          <ThetaInput
            value={placement.params.theta ?? 0}
            onChange={(v) => updateGateParams(placement.id, { theta: v })}
            onClose={() => setEditing(false)}
          />
        </div>
      )}
    </div>
  );
}

function CnotControlChip({
  placement,
  stepMode,
  currentStep,
  stepOrder,
}: {
  placement: GatePlacement;
  stepMode: boolean;
  currentStep: number;
  stepOrder: number;
}): JSX.Element {
  const removeGate = useCircuitStore((s) => s.removeGate);
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `placement-${placement.id}`,
    data: {
      source: "placement",
      placementId: placement.id,
      gateType: placement.gateType,
      takesTheta: false,
      arity: 2,
    },
  });
  const left = WIRE_LEFT_PAD + placement.timeStep * COLUMN_WIDTH + COLUMN_WIDTH / 2 - 8;
  const dimmed = stepMode && stepOrder >= currentStep;
  return (
    <div
      className={`group absolute top-1/2 z-10 -translate-y-1/2 ${dimmed ? "opacity-30" : "opacity-100"} ${
        isDragging ? "opacity-30" : ""
      }`}
      style={{ left }}
    >
      <button
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        type="button"
        className="block h-4 w-4 cursor-grab rounded-full active:cursor-grabbing"
        style={{
          backgroundColor: "var(--gate-cnot)",
          boxShadow: "0 0 12px rgba(220,38,38,0.4)",
          touchAction: "none",
        }}
        aria-label="CNOT control"
      />
      <button
        type="button"
        onClick={() => removeGate(placement.id)}
        className="absolute -right-2 -top-2 hidden h-4 w-4 items-center justify-center rounded-full bg-bg-base text-[9px] text-text-secondary ring-1 ring-border hover:bg-red-500/20 hover:text-red-300 group-hover:flex"
        aria-label="remove CNOT"
      >
        ×
      </button>
    </div>
  );
}

function CnotTargetChip({
  placement,
  stepMode,
  currentStep,
  stepOrder,
}: {
  placement: GatePlacement;
  stepMode: boolean;
  currentStep: number;
  stepOrder: number;
}): JSX.Element {
  const left = WIRE_LEFT_PAD + placement.timeStep * COLUMN_WIDTH + COLUMN_WIDTH / 2 - 14;
  const dimmed = stepMode && stepOrder >= currentStep;
  return (
    <div
      className={`absolute top-1/2 z-10 -translate-y-1/2 ${dimmed ? "opacity-30" : "opacity-100"}`}
      style={{ left }}
    >
      <div
        className="flex h-7 w-7 items-center justify-center rounded-full border-2 bg-bg-surface"
        style={{ borderColor: "var(--gate-cnot)" }}
      >
        <span className="font-display text-sm" style={{ color: "var(--gate-cnot)" }}>
          ⊕
        </span>
      </div>
    </div>
  );
}

function CnotConnectors({ gates }: { gates: GatePlacement[] }): JSX.Element {
  const lines = gates.filter((g) => g.qubitTargets.length === 2);
  return (
    <svg
      className="pointer-events-none absolute inset-0"
      style={{ width: "100%", height: "100%" }}
    >
      {lines.map((g) => {
        const x = WIRE_LEFT_PAD + g.timeStep * COLUMN_WIDTH + COLUMN_WIDTH / 2;
        const [c, t] = g.qubitTargets;
        const y1 = c * ROW_HEIGHT + ROW_HEIGHT / 2;
        const y2 = t * ROW_HEIGHT + ROW_HEIGHT / 2;
        return (
          <line
            key={g.id}
            x1={x}
            y1={y1}
            x2={x}
            y2={y2}
            stroke="var(--gate-cnot)"
            strokeWidth={2}
            strokeOpacity={0.65}
          />
        );
      })}
    </svg>
  );
}
