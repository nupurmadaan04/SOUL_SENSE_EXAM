import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { ThemeProvider, NavbarController, BottomNavigation } from '@/components/layout';
import { NetworkErrorBanner } from '@/components/common';
import { AuthProvider } from '@/hooks/useAuth';
import QueryProvider from '@/components/providers/QueryProvider';
import { WebVitalsMonitor } from '@/components/monitoring';
import { SkipLinks } from '@/components/accessibility';
import { OfflineBanner } from '@/components/offline';
import { SessionTimeoutWarning } from '@/components/SessionTimeoutWarning';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });

export const metadata: Metadata = {
  title: 'Soul Sense | AI-Powered Emotional Intelligence Test',
  description:
    'Discover your emotional intelligence with Soul Sense. Get deep insights into your EQ, build better relationships, and unlock your full potential using our AI-powered analysis.',
  keywords: [
    'EQ Test',
    'Emotional Intelligence',
    'AI Assessment',
    'Self-Awareness',
    'Professional Growth',
  ],
  authors: [{ name: 'Soul Sense' }],
  creator: 'Soul Sense',
  publisher: 'Soul Sense',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3005'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: '/',
    title: 'Soul Sense | AI-Powered Emotional Intelligence Test',
    description: 'Discover your emotional intelligence with Soul Sense',
    siteName: 'Soul Sense',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Soul Sense | AI-Powered Emotional Intelligence Test',
    description: 'Discover your emotional intelligence with Soul Sense',
  },
  robots: {
    index: true,
    follow: true,
  },
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Soul Sense',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: true,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
  colorScheme: 'light dark',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                // Theme initialization
                if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                } else if (localStorage.theme === 'light') {
                  document.documentElement.classList.remove('dark');
                  document.documentElement.classList.add('light');
                }
                // Font size initialization
                const fontSize = localStorage.getItem('soulsense_font_size');
                if (fontSize && ['small', 'medium', 'large'].includes(fontSize)) {
                  document.documentElement.classList.add('font-size-' + fontSize);
                }
                // High contrast initialization
                if (localStorage.getItem('soulsense_high_contrast') === 'true') {
                  document.documentElement.classList.add('high-contrast');
                }
                // Reduced motion initialization
                if (localStorage.getItem('soulsense_reduced_motion') === 'true') {
                  document.documentElement.classList.add('reduced-motion');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body className={`${inter.variable} font-sans antialiased`} suppressHydrationWarning>
        <WebVitalsMonitor />
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SkipLinks />
          <Toaster
            position="top-right"
            richColors
            closeButton
            className="z-[9999]"
            toastOptions={{
              style: {
                background: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                color: 'hsl(var(--foreground))',
              },
            }}
          />
          <QueryProvider>
            <AuthProvider>
              <SessionTimeoutWarning />
              <OfflineBanner />
              <NetworkErrorBanner />
              <NavbarController />
              <div id="main-content" role="main" tabIndex={-1}>
                {children}
              </div>
              <BottomNavigation />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
