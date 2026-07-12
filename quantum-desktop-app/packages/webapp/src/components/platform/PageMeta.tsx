import { useEffect } from "react";
import { APP_TITLE, CREATOR } from "../../config/attribution";

interface PageMetaProps {
  title: string;
  description?: string;
}

/** Sets document title and core SEO metadata. */
export function PageMeta({ title, description }: PageMetaProps): null {
  useEffect(() => {
    document.title = title === "QuantumLab" || title === APP_TITLE ? APP_TITLE : `${title} | ${APP_TITLE}`;

    const setMeta = (name: string, content: string) => {
      let meta = document.querySelector(`meta[name="${name}"]`);
      if (!meta) {
        meta = document.createElement("meta");
        meta.setAttribute("name", name);
        document.head.appendChild(meta);
      }
      meta.setAttribute("content", content);
    };

    if (description) {
      setMeta("description", description);
    }
    setMeta("author", CREATOR.name);
    setMeta(
      "keywords",
      "Quantum Computing, Quantum Mechanics, Quantum Simulator, Education, Physics, Qubits, QuantumLab",
    );
  }, [title, description]);
  return null;
}

