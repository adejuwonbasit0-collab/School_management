import type { Metadata } from 'next';
import { Providers } from '@/components/layout/providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: { default: 'EduCore', template: '%s | EduCore' },
  description: 'Enterprise School Management Platform',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
