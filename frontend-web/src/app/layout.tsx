import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { ThemeProvider } from '@/components/layout';
import { NavbarController } from '@/components/layout/navbar-controller';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

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
};

import { AuthProvider } from '@/hooks/useAuth';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <NavbarController />
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
