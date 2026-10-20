import { useEffect, useState } from "react";
import { PageMeta } from "../../components/platform/PageMeta";
import { api, formatDate } from "../client";
import { useAsync } from "../hooks";
import type { NewsFeed } from "../types";
import { ErrorState, LoadingPanel } from "../components/ui";

const CATEGORY_LABELS: Record<string, string> = {
  research: "Research",
  hardware: "Hardware",
  software: "Software",
  qec: "Error correction",
  benchmarks: "Benchmarks",
  reproducibility: "Reproducibility",
  algorithms: "Algorithms",
};

export default function CommunityPage(): JSX.Element {
  const [category, setCategory] = useState("");
  const [feed, setFeed] = useState<NewsFeed | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = new URLSearchParams({ limit: "30" });
  if (category) query.set("category", category);

  const state = useAsync(
    (signal) => api<NewsFeed>(`/community/news?${query.toString()}`, { signal }),
    [category],
  );

  useEffect(() => {
    setLoading(state.loading);
    setError(state.error ? state.error.message : null);
    if (state.data) setFeed(state.data);
  }, [state.loading, state.error, state.data]);

  const categories = Array.from(
    new Set((feed?.items ?? []).map((item) => item.category)),
  );

  return (
    <>
      <PageMeta
        title="Community"
        description="Verified quantum computing news and community projects on QuantHub."
      />
      <div className="qh-container py-6">
        <header className="mb-4">
          <h1 className="m-0 text-[20px] font-semibold">Community</h1>
          <p className="qh-subtle m-0">
            Verified headlines from primary sources, plus the projects people are publishing.
          </p>
        </header>

        {feed && (
          <div className="mb-4 rounded border border-[#30363d] bg-[#161b22] p-3 text-[12px]">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`qh-badge ${feed.feed.live ? "qh-badge-public" : "qh-badge-accent"}`}>
                {feed.feed.live ? "Live feed" : "Curated snapshot"}
              </span>
              <span className="text-[#9198a1]">{feed.feed.label}</span>
              {feed.feed.fetched_at && (
                <span className="text-[#6e7681]">fetched {formatDate(feed.feed.fetched_at)}</span>
              )}
            </div>
            {feed.feed.warning && (
              <p className="mb-0 mt-2 text-[#e3b341]">{feed.feed.warning}</p>
            )}
            <p className="mb-0 mt-2 text-[11px] text-[#6e7681]">{feed.attribution}</p>
          </div>
        )}

        <div className="mb-4 flex flex-wrap gap-1.5">
          <button
            type="button"
            className="qh-topic"
            data-active={category === ""}
            style={category === "" ? { borderColor: "#58a6ff", color: "#79c0ff" } : undefined}
            onClick={() => setCategory("")}
          >
            All
          </button>
          {categories.map((item) => (
            <button
              key={item}
              type="button"
              className="qh-topic"
              data-active={category === item}
              style={category === item ? { borderColor: "#58a6ff", color: "#79c0ff" } : undefined}
              onClick={() => setCategory(item)}
            >
              {CATEGORY_LABELS[item] ?? item}
            </button>
          ))}
        </div>

        {loading && !feed && <LoadingPanel rows={6} />}
        {error && !feed && <ErrorState message={error} onRetry={state.reload} />}

        <div className="grid gap-3 lg:grid-cols-2">
          {(feed?.items ?? []).map((item) => (
            <article key={item.id} className="qh-card qh-card-body">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] text-[#8b949e]">
                <span className="qh-badge">{CATEGORY_LABELS[item.category] ?? item.category}</span>
                <span>{item.source}</span>
                {item.published_at && <span>· {formatDate(item.published_at)}</span>}
                {item.verification && (
                  <span className="ml-auto text-[#3fb950]" title={item.verification}>
                    verified
                  </span>
                )}
              </div>
              <h2 className="m-0 text-[14px] font-semibold">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="text-[#e6edf3] hover:text-[#79c0ff]"
                >
                  {item.title}
                </a>
              </h2>
              <p className="mb-2 mt-1 text-[12px] text-[#9198a1]">{item.summary}</p>
              <div className="flex flex-wrap items-center gap-1.5">
                {item.tags.map((tag) => (
                  <span key={tag} className="qh-topic">
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>

        {feed && feed.items.length === 0 && (
          <p className="qh-help">No verified items in this category.</p>
        )}
      </div>
    </>
  );
}
