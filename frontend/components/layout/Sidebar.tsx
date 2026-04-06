'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  Wifi,
  Radio,
  Zap,
  Key,
  Skull,
  Globe,
  Target,
  Shield,
} from 'lucide-react'

const NAV = [
  { href: '/',              label: 'Dashboard',     icon: LayoutDashboard },
  { href: '/interfaces',   label: 'Interfaces',    icon: Wifi             },
  { href: '/scanner',      label: 'Escáner',       icon: Radio            },
  { href: '/handshake',    label: 'Handshake',     icon: Zap              },
  { href: '/cracking',     label: 'Cracking',      icon: Key              },
  { href: '/deauth',       label: 'Deauth',        icon: Skull            },
  { href: '/evil-portal',  label: 'Evil Portal',   icon: Globe            },
  { href: '/campaigns',    label: 'Campañas',      icon: Target           },
]

export function Sidebar() {
  const path = usePathname()

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-surface border-r border-border/60 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border/60">
        <div className="p-2 rounded-lg bg-accent/10 text-accent">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <p className="font-bold text-text tracking-wider font-mono">WifiPwn</p>
          <p className="text-[10px] text-muted uppercase tracking-widest">v1.0 · Pentesting</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== '/' && path.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                active
                  ? 'bg-accent/10 text-accent border border-accent/20'
                  : 'text-muted hover:text-text hover:bg-card'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
              {active && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border/60">
        <p className="text-[10px] text-muted/50 font-mono text-center">
          USE RESPONSIBLY · AUTHORIZED ONLY
        </p>
      </div>
    </aside>
  )
}
