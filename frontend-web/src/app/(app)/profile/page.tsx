export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground mt-2">Manage your personal information.</p>
      </div>

      <div className="rounded-lg border bg-card p-8">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="h-20 w-20 rounded-full bg-muted"></div>
            <div>
              <p className="font-semibold">Test User</p>
              <p className="text-muted-foreground text-sm">user@example.com</p>
            </div>
          </div>
          <button className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
            Edit Profile
          </button>
        </div>
      </div>
    </div>
  );
}
