import './globals.css';

export const metadata = {
  title: 'UnMask — Anatomy Tutor',
  description: 'Socratic NBCOT-prep tutor with progressive context revelation',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
