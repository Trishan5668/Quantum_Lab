import { useEffect, useRef } from "react";
import Editor from "@monaco-editor/react";
import type { Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import type { EditorLanguageId } from "../../store/editorStore";

const MONACO_LANGUAGE: Record<EditorLanguageId, string> = {
  qiskit: "python",
  qsharp: "qsharp",
};

function registerQSharpLanguage(monaco: Monaco): void {
  if (monaco.languages.getLanguages().some((lang: { id: string }) => lang.id === "qsharp")) {
    return;
  }

  monaco.languages.register({ id: "qsharp" });
  monaco.languages.setMonarchTokensProvider("qsharp", {
    defaultToken: "",
    keywords: [
      "operation",
      "function",
      "body",
      "adjoint",
      "controlled",
      "newtype",
      "struct",
      "namespace",
      "open",
      "use",
      "mutable",
      "set",
      "let",
      "if",
      "elif",
      "else",
      "for",
      "in",
      "while",
      "repeat",
      "until",
      "return",
      "fail",
      "within",
      "apply",
      "is",
      "self",
      "auto",
      "true",
      "false",
      "Unit",
      "Int",
      "Double",
      "Bool",
      "String",
      "Result",
      "Pauli",
      "Qubit",
    ],
    builtins: [
      "H",
      "X",
      "Y",
      "Z",
      "CNOT",
      "CX",
      "Message",
      "M",
      "MResetZ",
      "MResetX",
      "MResetY",
      "Reset",
      "ResetAll",
      "Length",
    ],
    tokenizer: {
      root: [
        [/\/\/.*$/, "comment"],
        [/\$"([^"\\]|\\.)*"/, "string"],
        [/"([^"\\]|\\.)*"/, "string"],
        [/\b(operation|function|namespace|open|use|let|mutable|set|if|else|return)\b/, "keyword"],
        [/\b(H|X|Y|Z|CNOT|CX|Message|MResetZ|MResetX|MResetY|Reset|ResetAll)\b/, "type.identifier"],
        [/\b\d+(\.\d+)?\b/, "number"],
        [/[{}()\[\]]/, "@brackets"],
      ],
    },
  });
}

interface CodeEditorProps {
  language: EditorLanguageId;
  value: string;
  onChange: (value: string) => void;
}

export function CodeEditor({ language, value, onChange }: CodeEditorProps): JSX.Element {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    editorRef.current?.layout();
  }, [language]);

  return (
    <Editor
      height="100%"
      language={MONACO_LANGUAGE[language]}
      value={value}
      theme="vs-dark"
      onChange={(next: string | undefined) => onChange(next ?? "")}
      beforeMount={(monaco: Monaco) => {
        registerQSharpLanguage(monaco);
        monaco.editor.defineTheme("quantumlab-dark", {
          base: "vs-dark",
          inherit: true,
          rules: [],
          colors: {
            "editor.background": "#0a0b0f",
            "editor.lineHighlightBackground": "#12141a",
            "editorLineNumber.foreground": "#64748b",
            "editorCursor.foreground": "#a78bfa",
            "editor.selectionBackground": "#7c3aed44",
          },
        });
      }}
      onMount={(instance: editor.IStandaloneCodeEditor, monaco: Monaco) => {
        editorRef.current = instance;
        monaco.editor.setTheme("quantumlab-dark");
      }}
      options={{
        minimap: { enabled: false },
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: 13,
        lineNumbers: "on",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        bracketPairColorization: { enabled: true },
        padding: { top: 12, bottom: 12 },
        tabSize: 4,
        wordWrap: "on",
      }}
    />
  );
}
