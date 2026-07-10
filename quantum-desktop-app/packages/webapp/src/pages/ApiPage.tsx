import { Link } from "react-router-dom";
import { PageMeta } from "../components/platform/PageMeta";
import { SectionHeader } from "../components/platform/SectionHeader";
import { API_BASE_URL, backendUrl } from "../config/api";

export default function ApiPage(): JSX.Element {
  return (
    <>
      <PageMeta
        title="API Reference"
        description="FastAPI v1 and v2 endpoints for circuit simulation, visualization, and metrics."
      />
      <div className="platform-container max-w-3xl py-12 sm:py-16">
        <SectionHeader
          eyebrow="API"
          title="HTTP API Reference"
          subtitle="JSON-over-HTTP bridge to the quantumlab Python engine."
        />

        <div className="space-y-6">
          <section className="platform-card p-6">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Base URL
            </h3>
            <code className="mt-2 block break-all font-mono text-sm text-accent-glow">
              {API_BASE_URL}
            </code>
          </section>

          <section className="platform-card p-6">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              v1 Endpoints
            </h3>
            <ul className="mt-3 space-y-2 font-mono text-xs text-text-secondary">
              <li>GET /api/v1/health</li>
              <li>POST /api/v1/circuit/run</li>
              <li>POST /api/v1/circuit/step</li>
              <li>POST /api/v1/visualize/bloch</li>
              <li>POST /api/v1/visualize/density</li>
              <li>POST /api/v1/explain (SSE)</li>
            </ul>
          </section>

          <section className="platform-card p-6">
            <h3 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              v2 Endpoints
            </h3>
            <ul className="mt-3 space-y-2 font-mono text-xs text-text-secondary">
              <li>POST /api/v2/circuit/run</li>
              <li>POST /api/v2/metrics/fidelity</li>
              <li>POST /api/v2/metrics/entropy</li>
              <li>POST /api/v2/metrics/purity</li>
            </ul>
          </section>

          <p className="text-sm text-text-muted">
            Interactive OpenAPI documentation is available at{" "}
            <a
              href={backendUrl("/docs")}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-measure hover:underline"
            >
              /docs
            </a>{" "}
            when the server is running.
          </p>
        </div>

        <Link to="/docs/api-v1" className="btn btn-secondary btn-md mt-8">
          Full API Documentation
        </Link>
      </div>
    </>
  );
}
