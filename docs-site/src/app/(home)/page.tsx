import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center text-center flex-1 px-6 py-16">
      {/* Hero Section */}
      <div className="max-w-3xl">
        <h1 className="text-5xl font-bold tracking-tight mb-6 bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent">
          Anvesh
        </h1>
        <p className="text-xl text-muted-foreground mb-4">
          Lead Generation Engine
        </p>
        <p className="text-lg text-muted-foreground/80 mb-8">
          Hunt for high-value businesses with zero online presence. 
          Automate lead scraping from Google Maps and export to CSV.
        </p>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center flex-wrap">
          <Link
            href="/docs"
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
          >
            Get Started
          </Link>
          <Link
            href="/docs/api"
            className="px-6 py-3 border border-border rounded-lg font-medium hover:bg-accent transition-colors"
          >
            API Reference
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl">
        <div className="p-6 rounded-xl border border-border bg-card">
          <div className="text-3xl mb-3">🔍</div>
          <h3 className="font-semibold mb-2">Smart Scraping</h3>
          <p className="text-sm text-muted-foreground">
            Scrape Google Maps for leads based on industry and location.
          </p>
        </div>
        <div className="p-6 rounded-xl border border-border bg-card">
          <div className="text-3xl mb-3">⚡</div>
          <h3 className="font-semibold mb-2">Background Tasks</h3>
          <p className="text-sm text-muted-foreground">
            Run multiple scraping tasks in parallel with real-time status.
          </p>
        </div>
        <div className="p-6 rounded-xl border border-border bg-card">
          <div className="text-3xl mb-3">📊</div>
          <h3 className="font-semibold mb-2">Easy Export</h3>
          <p className="text-sm text-muted-foreground">
            Export all leads to CSV for use in your CRM or outreach tools.
          </p>
        </div>
      </div>
    </div>
  );
}
