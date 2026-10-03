import { useMemo } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { useCircuitStore } from "../../store/circuitStore";
import { selectCurrentCode, useEditorStore } from "../../store/editorStore";
import { ReportReader } from "../Reports/ReportReader";
import {
  buildCodeReport,
  buildCodeReportMetadata,
  codeReportDocumentTitle,
  codeReportHeaderSubtitle,
} from "./codeReport";

interface EditorCodeReportModalProps {
  open: boolean;
  onClose: () => void;
}

export function EditorCodeReportModal({ open, onClose }: EditorCodeReportModalProps): JSX.Element | null {
  const language = useEditorStore((s) => s.language);
  const code = useEditorStore(selectCurrentCode);
  const outputState = useEditorStore((s) => s.outputState);
  const outputText = useEditorStore((s) => s.outputText);
  const errorText = useEditorStore((s) => s.errorText);
  const numQubits = useCircuitStore((s) => s.numQubits);
  const initialBasisState = useCircuitStore((s) => s.initialBasisState);
  const gates = useCircuitStore((s) => s.gates);
  const { profile, user } = useAuth();

  const reportInput = useMemo(
    () => ({
      language,
      code,
      numQubits,
      initialBasisState,
      gates,
      outputState,
      outputText,
      errorText,
      authorName: profile?.name ?? user?.displayName ?? user?.email ?? undefined,
      authorId: profile?.uid ?? user?.uid,
    }),
    [
      code,
      errorText,
      gates,
      initialBasisState,
      language,
      numQubits,
      outputState,
      outputText,
      profile?.name,
      profile?.uid,
      user?.displayName,
      user?.email,
      user?.uid,
    ],
  );

  const sections = useMemo(() => buildCodeReport(reportInput), [reportInput]);
  const metadata = useMemo(() => buildCodeReportMetadata(reportInput), [reportInput]);
  const subtitle = codeReportHeaderSubtitle(reportInput);
  const documentTitle = codeReportDocumentTitle(language);

  if (!open) return null;

  return (
    <div className="report-modal" role="dialog" aria-modal="true" aria-label="QuantumLab code report">
      <div className="report-modal-panel">
        <header className="report-modal-header">
          <div className="min-w-0">
            <p className="report-eyebrow">QUANTUMLAB CODE REPORT</p>
            <h2>{documentTitle}</h2>
            <p>{subtitle}</p>
            <p className="text-[11px] text-text-muted">
              Generated: {new Date(metadata.generatedAt ?? Date.now()).toLocaleString()}
            </p>
          </div>
          <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="report-modal-body">
          <div className="physics-report-surface code-report-surface physics-report-fullscreen">
            <ReportReader
              title="QuantumLab Code Report"
              subtitle={subtitle}
              sections={sections}
              metadata={metadata}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
