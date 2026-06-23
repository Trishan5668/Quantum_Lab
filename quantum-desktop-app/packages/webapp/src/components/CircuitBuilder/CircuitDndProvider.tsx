import { useCallback, useState, type ReactNode } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useCircuitStore } from "../../store/circuitStore";
import { gateMeta, type GateType } from "../../types";
import { ThetaModal } from "./ThetaControls";

export interface ActiveDragData {
  source: "palette" | "placement";
  gateType: GateType;
  takesTheta: boolean;
  arity: 1 | 2;
  placementId?: string;
}

interface CellDropData {
  type: "cell";
  qubit: number;
  timeStep: number;
}

export function CircuitDndProvider({ children }: { children: ReactNode }): JSX.Element {
  // Use Mouse + Touch separately so each sensor has its own activation
  // constraint -- touch needs a delay to avoid stealing scroll gestures,
  // mouse fires immediately on a small drag distance for snappy feel.
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 3 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 120, tolerance: 5 } }),
    useSensor(KeyboardSensor),
  );

  const numQubits = useCircuitStore((s) => s.numQubits);
  const addGate = useCircuitStore((s) => s.addGate);
  const moveGate = useCircuitStore((s) => s.moveGate);

  const [active, setActive] = useState<ActiveDragData | null>(null);
  const [thetaPrompt, setThetaPrompt] = useState<{
    gateType: GateType;
    qubit: number;
    timeStep: number;
  } | null>(null);

  const handleDragStart = (e: DragStartEvent) => {
    const data = e.active.data.current as ActiveDragData | undefined;
    if (data) setActive(data);
  };

  const handleDragCancel = () => setActive(null);

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      setActive(null);
      const activeData = e.active.data.current as ActiveDragData | undefined;
      const overData = e.over?.data.current as CellDropData | undefined;
      if (!activeData || !overData || overData.type !== "cell") return;

      if (activeData.source === "palette") {
        const meta = gateMeta(activeData.gateType);
        if (meta.arity === 2) {
          if (overData.qubit + 1 >= numQubits) return;
          addGate(
            activeData.gateType,
            [overData.qubit, overData.qubit + 1],
            overData.timeStep,
          );
          return;
        }
        if (meta.takesTheta) {
          setThetaPrompt({
            gateType: activeData.gateType,
            qubit: overData.qubit,
            timeStep: overData.timeStep,
          });
          return;
        }
        addGate(activeData.gateType, [overData.qubit], overData.timeStep);
        return;
      }

      if (activeData.source === "placement" && activeData.placementId) {
        if (activeData.arity === 2 && overData.qubit + 1 >= numQubits) return;
        const targets =
          activeData.arity === 2
            ? [overData.qubit, Math.min(overData.qubit + 1, numQubits - 1)]
            : [overData.qubit];
        moveGate(activeData.placementId, overData.timeStep, targets);
      }
    },
    [addGate, moveGate, numQubits],
  );

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragCancel={handleDragCancel}
      onDragEnd={handleDragEnd}
    >
      {children}
      <DragOverlay
        dropAnimation={null}
        zIndex={1000}
        style={{ pointerEvents: "none" }}
      >
        {active ? <DragChip data={active} /> : null}
      </DragOverlay>
      {thetaPrompt && (
        <ThetaModal
          initial={Math.PI / 2}
          gateLabel={thetaPrompt.gateType}
          onCancel={() => setThetaPrompt(null)}
          onConfirm={(theta) => {
            addGate(
              thetaPrompt.gateType,
              [thetaPrompt.qubit],
              thetaPrompt.timeStep,
              theta,
            );
            setThetaPrompt(null);
          }}
        />
      )}
    </DndContext>
  );
}

function DragChip({ data }: { data: ActiveDragData }): JSX.Element {
  const meta = gateMeta(data.gateType);

  if (data.gateType === "CNOT") {
    return (
      <div
        className="flex select-none flex-col items-center gap-0.5 rounded-md border-2 bg-bg-surface/95 px-3 py-2 shadow-2xl backdrop-blur"
        style={{
          borderColor: meta.color,
          boxShadow: `0 0 0 1px ${meta.color}55, 0 0 24px ${meta.color}66`,
          cursor: "grabbing",
        }}
      >
        <span
          className="h-3 w-3 rounded-full"
          style={{ backgroundColor: meta.color }}
        />
        <span className="h-3 w-px" style={{ backgroundColor: meta.color }} />
        <span
          className="flex h-5 w-5 items-center justify-center rounded-full border-2 text-xs font-semibold"
          style={{ borderColor: meta.color, color: meta.color }}
        >
          ⊕
        </span>
      </div>
    );
  }

  return (
    <div
      className="flex select-none flex-col items-center justify-center rounded-md border-2 bg-bg-surface/95 px-3 py-2 shadow-2xl backdrop-blur"
      style={{
        borderColor: meta.color,
        boxShadow: `0 0 0 1px ${meta.color}55, 0 0 24px ${meta.color}66`,
        cursor: "grabbing",
      }}
    >
      <span
        className="font-display text-base font-semibold leading-none"
        style={{ color: meta.color }}
      >
        {meta.label}
      </span>
    </div>
  );
}
