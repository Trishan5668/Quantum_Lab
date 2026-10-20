import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

/**
 * Render untrusted Markdown safely.
 *
 * - Markdown is parsed with `marked` (no raw HTML execution).
 * - Output is sanitised with DOMPurify, allowing only safe tags/attributes.
 * - Links are forced to `https`/`http` and open in a new tab with
 *   `rel="noopener noreferrer nofollow"`; `javascript:` and `data:` URLs are
 *   removed by the sanitiser.
 */
export function Markdown({ source }: { source: string }): JSX.Element {
  const html = useMemo(() => {
    const rendered = marked.parse(source, { async: false, gfm: true, breaks: false }) as string;
    const clean = DOMPurify.sanitize(rendered, {
      ALLOWED_TAGS: [
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr", "strong", "em", "del", "blockquote",
        "ul", "ol", "li", "code", "pre", "a", "img", "table", "thead", "tbody", "tr", "th", "td",
        "span", "div", "input",
      ],
      ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "align", "type", "checked", "disabled", "target", "rel"],
      ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#|\/)/i,
      FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form"],
    });
    return clean;
  }, [source]);

  return (
    <div
      className="qh-markdown"
      onClick={handleLinkClick}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/** Route link clicks to a new tab without relying on injected markup. */
function handleLinkClick(event: React.MouseEvent<HTMLDivElement>): void {
  const target = event.target as HTMLElement | null;
  const anchor = target?.closest("a");
  if (!anchor) return;
  const href = anchor.getAttribute("href") ?? "";
  if (href.startsWith("#")) return;
  if (/^https?:/i.test(href)) {
    anchor.setAttribute("target", "_blank");
    anchor.setAttribute("rel", "noopener noreferrer nofollow");
  }
}
