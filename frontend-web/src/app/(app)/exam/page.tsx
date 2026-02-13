export default function ExamPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Take Exam</h1>
        <p className="text-muted-foreground mt-2">Start a new emotional intelligence assessment.</p>
      </div>

      <div className="rounded-lg border bg-card p-8 text-center">
        <p className="text-muted-foreground mb-4">No active exam in progress</p>
        <button className="inline-block px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          Start New Exam
        </button>
      </div>
    </div>
  );
}
