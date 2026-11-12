import { useState } from 'react'
import Navigation, { sections, type Destination } from './Navigation'
import Dashboard from './Dashboard'
import Inventory from './Inventory'
import Recipes from './Recipes'
import Availability from './Availability'
import Shopping from './Shopping'
import { Icon } from './ui'

export default function App() {
  const [destination, setDestination] = useState<Destination>({ section: 'home' })
  const { section } = destination
  const label = sections.find((entry) => entry.section === section)!.label
  const key = section + (destination.action ?? '') + (destination.recipeId ?? destination.listId ?? '')
    + (destination.inventoryFilter ?? '')
  const date = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Saltar al contenido</a>
      <Navigation active={section} onNavigate={setDestination} />
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><Icon name="home" /><span>Mi cocina /</span><strong>{label}</strong></div>
          <span className="topbar-date">{date}</span>
        </header>
        <main id="main-content" className="page-content" tabIndex={-1}>
          {section === 'home' && <Dashboard onNavigate={setDestination} />}
          {section === 'inventory' && <Inventory key={key} initialCreate={destination.action === 'create'}
            initialExpiration={destination.inventoryFilter === 'expiring_soon' ? 'expiring_soon' : 'all'}
            initialStock={destination.inventoryFilter === 'low_stock' ? 'low_stock' : 'all'} />}
          {section === 'recipes' && <Recipes key={key} initialCreate={destination.action === 'create'} initialRecipeId={destination.recipeId} />}
          {section === 'availability' && <Availability />}
          {section === 'shopping' && <Shopping key={key} initialCreate={destination.action === 'create'}
            initialListId={destination.listId} initialFilter={destination.filter} />}
        </main>
      </div>
    </div>
  )
}
