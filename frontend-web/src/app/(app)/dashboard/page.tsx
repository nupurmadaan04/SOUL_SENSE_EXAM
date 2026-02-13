export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-2">Welcome back! Here's your dashboard overview.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border bg-card p-6">
          <h3 className="font-semibold text-sm">Total Tests Taken</h3>
          <p className="text-3xl font-bold mt-2">8</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <h3 className="font-semibold text-sm">Average Score</h3>
          <p className="text-3xl font-bold mt-2">78%</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <h3 className="font-semibold text-sm">Journal Entries</h3>
          <p className="text-3xl font-bold mt-2">24</p>
        </div>
        <div className="rounded-lg border bg-card p-6">
          <h3 className="font-semibold text-sm">Streak</h3>
          <p className="text-3xl font-bold mt-2">5 days</p>
        </div>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <p className="text-muted-foreground">Your recent activity will appear here.</p>
      </div>
    </div>
  );
}
