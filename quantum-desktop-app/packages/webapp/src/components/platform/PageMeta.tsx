import { useEffect } from "react";

interface PageMetaProps {
  title: string;
  description?: string;
}

/** Sets document title and meta description for SEO. */
export function PageMeta({ title, description }: PageMetaProps): null {
  useEffect(() => {
    document.title = title.includes("QuantumLab") ? title : `${title} · QuantumLab`;
    if (description) {
      let meta = document.querySelector('meta[name="description"]');
      if (!meta) {
        meta = document.createElement("meta");
        meta.setAttribute("name", "description");
        document.head.appendChild(meta);
      }
      meta.setAttribute("content", description);
    }
  }, [title, description]);
  return null;
}
