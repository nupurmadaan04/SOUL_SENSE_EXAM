export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">Manage your preferences and account settings.</p>
      </div>

      <div className="rounded-lg border bg-card p-8 space-y-6">
        <div>
          <h3 className="font-semibold mb-2">Notifications</h3>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="rounded" />
            <span className="text-sm">Email notifications</span>
          </label>
        </div>

        <div>
          <h3 className="font-semibold mb-2">Privacy</h3>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="rounded" />
            <span className="text-sm">Public profile</span>
          </label>
        </div>

        <div>
          <h3 className="font-semibold mb-2">Language</h3>
          <select className="px-3 py-2 rounded border bg-background text-foreground">
            <option>English</option>
            <option>Spanish</option>
            <option>French</option>
          </select>
        </div>

        <button className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          Save Settings
        </button>
      </div>
    </div>
  );
}
