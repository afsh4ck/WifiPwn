import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { WifiProvider } from '@/lib/context'

export const metadata: Metadata = {
  title: 'WifiPwn v2',
  description: 'WiFi Pentesting Suite',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="dark">
      <body className="bg-bg text-text antialiased">
        <WifiProvider>
          <div className="flex min-h-screen bg-grid-overlay">
            <Sidebar />
            <div className="flex flex-col flex-1 min-w-0">
              <Header />
              <main className="flex-1 overflow-auto p-6">
                {children}
              </main>
            </div>
          </div>
        </WifiProvider>
      </body>
    </html>
  )
}
