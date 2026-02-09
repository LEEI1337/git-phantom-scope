import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Git Phantom Scope - GitHub Profile Intelligence',
  description:
    'Privacy-First GitHub Profile Intelligence & AI-Powered Visual Identity Platform. Analyze any GitHub profile, detect AI-assisted code, and generate stunning visual identities.',
  keywords: [
    'GitHub',
    'profile',
    'AI',
    'developer',
    'visual identity',
    'infographic',
    'portfolio',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gps-bg text-gps-text min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
