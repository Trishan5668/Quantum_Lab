import { Link } from "react-router-dom";
import { formatDate } from "../client";
import type { NewsFeed } from "../types";
import { ErrorState, Skeleton } from "./ui";

export function NewsPanel({
  feed,
  loading,
  error,
  onRetry,
  limit = 5,
  showFilters = false,
}: {
  feed: NewsFeed | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  limit?: number;
  showFilters?: boolean;
}): JSX.Element {
  return (
    <section className="qh-card" aria-labelledby="qh-news-heading">
      <div className="qh-card-header">
        <h2 id="qh-news-heading" className="m-0 text-[13px] font-semibold">
          Trending in Quantum Community
        </h2>
        <span
          className={`qh-badge ${feed?.feed.live ? "qh-badge-public" : "qh-badge-accent"}`}
          title={feed?.feed.label}
        >
          {feed ? (feed.feed.live ? "Live" : "Curated") : "—"}
        </span>
      </div>

      {loading && (
        <div className="space-y-3 p-4">
          <Skeleton height={14} width="90%" />
          <Skeleton height={12} width="70%" />
          <Skeleton height={14} width="80%" />
          <Skeleton height={12} width="60%" />
        </div>
      )}

      {!loading && error && (
        <div className="p-4">
          <ErrorState message={error} onRetry={onRetry} />
        </div>
      )}

      {!loading && !error && feed && (
        <>
          {feed.feed.warning && (
            <p className="m-0 border-b border-[#21262d] bg-[rgba(210,153,34,0.08)] px-4 py-2 text-[11px] text-[#e3b341]">
              {feed.feed.warning}
            </p>
          )}
          <ul className="m-0 list-none divide-y divide-[#21262d] p-0">
            {feed.items.slice(0, limit).map((item) => (
              <li key={item.id} className="px-4 py-3">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="text-[13px] font-semibold leading-snug text-[#e6edf3] hover:text-[#79c0ff]"
                  style={{ textDecoration: "none" }}
                >
                  {item.title}
                </a>
                <p className="mt-1 mb-1.5 text-[12px] leading-snug text-[#9198a1]">{item.summary}</p>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#6e7681]">
                  <span className="font-medium text-[#9198a1]">{item.source}</span>
                  <span aria-hidden="true">·</span>
                  <span>{formatDate(item.published_at)}</span>
                  {item.tags.slice(0, showFilters ? 3 : 2).map((tag) => (
                    <span key={tag} className="qh-topic">
                      #{tag}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          {feed.items.length === 0 && (
            <p className="qh-empty m-0">No verified items match this filter.</p>
          )}
          <div className="border-t border-[#21262d] px-4 py-2 text-[11px] text-[#6e7681]">
            <Link to="/community">See all community news →</Link>
            <span className="mx-1">·</span>
            <span>{feed.feed.live ? "Live publisher feeds" : "Verified snapshot"}</span>
          </div>
        </>
      )}
    </section>
  );
}
