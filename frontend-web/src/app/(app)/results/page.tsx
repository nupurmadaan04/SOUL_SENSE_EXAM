export default function ResultsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Results</h1>
        <p className="text-muted-foreground mt-2">View your exam results and insights.</p>
      </div>

      <div className="rounded-lg border bg-card p-8">
        <div className="space-y-4">
          <div className="pb-4 border-b">
            <p className="font-semibold">Latest Assessment - Feb 12, 2026</p>
            <p className="text-muted-foreground text-sm">Score: 78%</p>
          </div>
          <div className="pb-4">
            <p className="font-semibold">Previous Result - Feb 5, 2026</p>
            <p className="text-muted-foreground text-sm">Score: 75%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
