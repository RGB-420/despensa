import { useState } from 'react'
import { Icon, type IconName } from './ui'

export type Section = 'home' | 'inventory' | 'recipes' | 'availability' | 'shopping'
export interface Destination {
  section: Section
  action?: 'create'
  recipeId?: number
  listId?: number
  filter?: 'pending' | 'all'
  inventoryFilter?: 'expiring_soon' | 'low_stock'
}

export const sections: { section: Section; label: string; icon: IconName }[] = [
  { section: 'home', label: 'Inicio', icon: 'home' },
  { section: 'inventory', label: 'Mi despensa', icon: 'pantry' },
  { section: 'recipes', label: 'Recetas', icon: 'recipes' },
  { section: 'availability', label: '¿Qué puedo cocinar?', icon: 'cook' },
  { section: 'shopping', label: 'Lista de la compra', icon: 'shopping' },
]

export default function Navigation({ active, onNavigate }: {
  active: Section; onNavigate: (destination: Destination) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <aside className="navigation">
      <div className="navigation-brand">
        <button className="brand-link" aria-label="Despensa, ir a Inicio" onClick={() => { onNavigate({ section: 'home' }); setOpen(false) }}>
          <span className="brand-symbol"><Icon name="leaf" /></span><span>Despensa</span>
        </button>
        <button className="mobile-menu-button secondary" aria-label="Menú de secciones" aria-expanded={open}
          aria-controls="main-navigation" onClick={() => setOpen(!open)}><Icon name="menu" />Menú</button>
      </div>
      <nav id="main-navigation" className={'navigation-links ' + (open ? 'is-open' : '')} aria-label="Secciones">
        <span className="nav-caption">MI COCINA</span>
        {sections.map((entry) => (
          <button key={entry.section} className={'nav-link ' + (entry.section === active ? 'active' : '')}
            aria-current={entry.section === active ? 'page' : undefined}
            onClick={() => { onNavigate({ section: entry.section }); setOpen(false) }}>
            <Icon name={entry.icon} /><span>{entry.label}</span>
          </button>
        ))}
      </nav>
      <div className="navigation-footer"><Icon name="leaf" /><span>Recetas, despensa y compra<br /><strong>Tu espacio personal</strong></span></div>
    </aside>
  )
}
