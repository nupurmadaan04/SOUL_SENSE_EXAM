export default function JournalPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Journal</h1>
        <p className="text-muted-foreground mt-2">Reflect on your emotional journey.</p>
      </div>

      <div className="rounded-lg border bg-card p-8 text-center">
        <p className="text-muted-foreground mb-4">No journal entries yet</p>
        <button className="inline-block px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          New Entry
        </button>
      </div>
    </div>
  );
}
