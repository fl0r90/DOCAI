import "./globals.css";
import { ThemeProvider } from "../lib/ThemeProvider";

export const metadata = {
  title: 'DocAI v0.6.5 ALPHA',
  description: 'Forensic Document Intelligence Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 transition-colors duration-300">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
