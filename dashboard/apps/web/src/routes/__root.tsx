import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router';
import type { QueryClient } from '@tanstack/react-query';

export interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b bg-card">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link to="/" className="text-xl font-bold text-foreground">
                Sales AI
              </Link>
              <div className="hidden md:flex md:gap-6">
                <Link
                  to="/"
                  className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground [&.active]:text-foreground"
                >
                  儀表板
                </Link>
                <Link
                  to="/conversations"
                  className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground [&.active]:text-foreground"
                >
                  對話記錄
                </Link>
                <Link
                  to="/reports/weekly"
                  className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground [&.active]:text-foreground"
                >
                  週報
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
