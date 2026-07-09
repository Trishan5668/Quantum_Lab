export function GridBackground(): JSX.Element {
  return (
    <div className="platform-grid-bg pointer-events-none absolute inset-0" aria-hidden>
      <div className="platform-grid-lines" />
    </div>
  );
}
