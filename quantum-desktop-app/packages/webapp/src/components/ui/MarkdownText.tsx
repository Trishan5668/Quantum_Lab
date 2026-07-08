import { useMemo, type ReactNode } from "react";

/** Lightweight markdown-ish renderer — no extra dependencies. */
export function MarkdownText({ text }: { text: string }): JSX.Element {
  const blocks = useMemo(() => parseMarkdown(text), [text]);

  return (
    <div className="markdown-body">
      {blocks.map((block, i) => {
        if (block.type === "code") {
          return (
            <pre key={i} className="markdown-code">
              <code>{block.content}</code>
            </pre>
          );
        }
        return (
          <p key={i} className="markdown-paragraph">
            {renderInline(block.content)}
          </p>
        );
      })}
    </div>
  );
}

type Block = { type: "para"; content: string } | { type: "code"; content: string };

function parseMarkdown(raw: string): Block[] {
  const parts = raw.split(/```/);
  const blocks: Block[] = [];
  parts.forEach((part, idx) => {
    const trimmed = part.trim();
    if (!trimmed) return;
    if (idx % 2 === 1) {
      blocks.push({ type: "code", content: trimmed.replace(/^\w+\n/, "") });
      return;
    }
    trimmed.split(/\n\n+/).forEach((para) => {
      if (para.trim()) blocks.push({ type: "para", content: para.trim() });
    });
  });
  if (blocks.length === 0 && raw.trim()) {
    blocks.push({ type: "para", content: raw.trim() });
  }
  return blocks;
}

function renderInline(text: string): ReactNode[] {
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return tokens.map((token, i) => {
    if (token.startsWith("`") && token.endsWith("`")) {
      return (
        <code key={i} className="markdown-inline-code">
          {token.slice(1, -1)}
        </code>
      );
    }
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={i}>{token.slice(2, -2)}</strong>;
    }
    return token;
  });
}
