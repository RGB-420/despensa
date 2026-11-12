import { useEffect, useState } from 'react'
import { errorMessage, request } from './api'
import { amount, formatDate } from './format'
import type { InventoryItem } from './Inventory'
import { classifications, type RecipeAvailability } from './Availability'
import type { Destination } from './Navigation'
import { EmptyState, ErrorState, Icon, LoadingState, PageHeader, StatusBadge, type IconName } from './ui'

interface DashboardData {
  evaluated_on: string
  expiration_window_days: number
  total_products: number
  expiring_products_count: number
  low_stock_count: number
  ready_recipes_count: number
  pending_shopping_count: number
  untransferred_purchases_count: number
  recipes_today: RecipeAvailability[]
  expiring_products: InventoryItem[]
  shopping_lists: {
    id: number; name: string; pending_count: number; purchased_count: number
    transferred_count: number; total_items: number; is_complete: boolean
  }[]
}

export default function Dashboard({ onNavigate }: { onNavigate: (destination: Destination) => void }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    request<DashboardData>('/dashboard', { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setData(result) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [refresh])

  const quickActions: { label: string; icon: IconName; destination: Destination }[] = [
    { label: 'Añadir producto', icon: 'pantry', destination: { section: 'inventory', action: 'create' } },
    { label: 'Crear receta', icon: 'recipes', destination: { section: 'recipes', action: 'create' } },
    { label: 'Generar lista de compra', icon: 'shopping', destination: { section: 'shopping', action: 'create' } },
    { label: 'Explorar recetas disponibles', icon: 'cook', destination: { section: 'availability' } },
  ]
  const statistics: { label: string; value: number; caption: string; icon: IconName; destination: Destination }[] = data ? [
    { label: 'En tu despensa', value: data.total_products, caption: 'Productos y lotes registrados', icon: 'pantry', destination: { section: 'inventory' } },
    { label: 'Caducan pronto', value: data.expiring_products_count, caption: 'Con existencias utilizables', icon: 'clock', destination: { section: 'inventory', inventoryFilter: 'expiring_soon' } },
    { label: 'Existencias bajas', value: data.low_stock_count, caption: 'En el mínimo o por debajo', icon: 'warning', destination: { section: 'inventory', inventoryFilter: 'low_stock' } },
    { label: 'Recetas listas', value: data.ready_recipes_count, caption: 'Con todos los ingredientes', icon: 'cook', destination: { section: 'availability' } },
    { label: 'Por comprar', value: data.pending_shopping_count, caption: 'Productos de tus listas', icon: 'shopping', destination: { section: 'shopping', filter: 'pending' } },
  ] : []

  return (
    <>
      <PageHeader title="Inicio" description="Lo que tienes, lo que puedes cocinar y lo que necesitas comprar.">
        <button onClick={() => onNavigate({ section: 'inventory', action: 'create' })}><Icon name="plus" />Añadir producto</button>
      </PageHeader>
      {loading && <LoadingState text="Preparando el resumen de tu cocina…" />}
      {error && <ErrorState message={error} onRetry={() => setRefresh((value) => value + 1)} />}
      {!loading && !error && data && (
        <>
          <div className="stats-grid">
            {statistics.map((statistic) => (
              <button className="stat-card" key={statistic.label} onClick={() => onNavigate(statistic.destination)}>
                <span className="stat-label"><span>{statistic.label}</span><Icon name={statistic.icon} /></span>
                <strong>{statistic.value}</strong><span className="stat-caption">{statistic.caption}</span>
              </button>
            ))}
          </div>
          <div className="dashboard-grid">
            <section className="panel dashboard-panel">
              <div className="section-heading"><h2><Icon name="cook" />¿Qué puedo cocinar hoy?</h2>
                <button className="text-button" onClick={() => onNavigate({ section: 'availability' })}>Ver todas<Icon name="arrow" /></button>
              </div>
              <p className="muted small-text">Primero, las recetas que ya tienen todo lo necesario.</p>
              {data.recipes_today.length ? (
                <ul className="dashboard-recipes">
                  {data.recipes_today.map((recipe) => (
                    <li key={recipe.recipe_id}>
                      <span className="recipe-symbol"><Icon name="recipes" /></span>
                      <div className="row-content">
                        <button className="text-button row-title" onClick={() => onNavigate({ section: 'recipes', recipeId: recipe.recipe_id })}>{recipe.recipe_name}</button>
                        <p className="recipe-meta"><span><Icon name="clock" />{recipe.preparation_minutes} min</span><span><Icon name="people" />{recipe.servings} {recipe.servings === 1 ? 'ración' : 'raciones'}</span></p>
                      </div>
                      <StatusBadge tone={recipe.classification === 'ready_to_cook' ? 'success' : 'warning'}>{classifications[recipe.classification]}</StatusBadge>
                    </li>
                  ))}
                </ul>
              ) : <EmptyState title="Tus próximas recetas están aquí">Añade recetas y productos para descubrir qué puedes cocinar.</EmptyState>}
            </section>
            <section className="panel dashboard-panel">
              <div className="section-heading"><h2><Icon name="clock" />Caducan pronto</h2>
                <button className="text-button" onClick={() => onNavigate({ section: 'inventory' })}>Ver despensa<Icon name="arrow" /></button>
              </div>
              <p className="muted small-text">Desde hoy hasta dentro de {data.expiration_window_days} días.</p>
              {data.expiring_products.length ? <ul className="dashboard-products">
                {data.expiring_products.map((item) => (
                  <li key={item.id}><span className="product-dot"><Icon name="leaf" /></span>
                    <div className="row-content"><strong>{item.name}</strong><p className="muted">{amount(item.quantity, item.unit)}</p></div>
                    <StatusBadge tone="warning">{item.expiration_date === data.evaluated_on ? 'Hoy' : formatDate(item.expiration_date!)}</StatusBadge>
                  </li>
                ))}
              </ul> : <EmptyState title="Sin caducidades próximas">Los productos con fecha y existencias aparecerán aquí.</EmptyState>}
            </section>
            <section className="panel dashboard-panel">
              <div className="section-heading"><h2><Icon name="shopping" />Tu compra</h2>
                <button className="text-button" onClick={() => onNavigate({ section: 'shopping' })}>Ver listas<Icon name="arrow" /></button>
              </div>
              {data.untransferred_purchases_count > 0 && <p className="notice">{data.untransferred_purchases_count} productos comprados esperan a que los añadas a tu despensa.</p>}
              {data.shopping_lists.length ? <ul className="dashboard-shopping">
                {data.shopping_lists.map((list) => (
                  <li key={list.id}>
                    <div className="section-heading"><strong>{list.name}</strong><StatusBadge tone={list.is_complete ? 'success' : 'neutral'}>{list.is_complete ? 'Comprada' : list.pending_count + ' pendientes'}</StatusBadge></div>
                    <progress aria-label={'Progreso de ' + list.name} value={list.purchased_count} max={list.total_items || 1} />
                    <div className="section-heading small-text"><span className="muted">{list.purchased_count} de {list.total_items} comprados · {list.transferred_count} en despensa</span>
                      <button className="text-button" onClick={() => onNavigate({ section: 'shopping', listId: list.id, filter: list.pending_count ? 'pending' : 'all' })}>{list.pending_count ? 'Ver pendientes' : 'Ver compra'}<Icon name="arrow" /></button>
                    </div>
                  </li>
                ))}
              </ul> : <EmptyState title="Prepara tu próxima compra" action={<button className="secondary" onClick={() => onNavigate({ section: 'shopping', action: 'create' })}>Crear lista de compra</button>}>Selecciona recetas y reúne lo que necesitas.</EmptyState>}
            </section>
            <section className="panel dashboard-panel">
              <div className="section-heading"><h2>Acciones rápidas</h2></div>
              <div className="quick-actions">
                {quickActions.map((action) => (
                  <button key={action.label} onClick={() => onNavigate(action.destination)}>
                    <span className="quick-icon"><Icon name={action.icon} /></span>
                    <span>{action.label}</span><Icon name="arrow" />
                  </button>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </>
  )
}
