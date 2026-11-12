import { useEffect, useState } from 'react'
import { deleteRecipe, errorMessage, getRecipe, listRecipes, request, type Recipe } from './api'
import RecipeForm from './RecipeForm'
import { classifications, type RecipeAvailability } from './Availability'
import { amount } from './format'
import { EmptyState, ErrorState, Icon, LoadingState, PageHeader, StatusBadge } from './ui'

type View = { page: 'list' | 'create' } | { page: 'detail' | 'edit'; recipe: Recipe }
const dateFormat = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })

export default function Recipes({ initialCreate = false, initialRecipeId }: {
  initialCreate?: boolean; initialRecipeId?: number
}) {
  const [view, setView] = useState<View>({ page: initialCreate ? 'create' : 'list' })
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [availability, setAvailability] = useState<Record<number, RecipeAvailability>>({})
  const [query, setQuery] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(Boolean(initialRecipeId))
  const [error, setError] = useState('')
  const page = view.page

  useEffect(() => {
    if (page !== 'list') return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    listRecipes(query, controller.signal)
      .then((items) => { if (!controller.signal.aborted) setRecipes(items) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [page, query, refresh])

  useEffect(() => {
    if (page !== 'list' && page !== 'detail') return
    const controller = new AbortController()
    request<RecipeAvailability[]>('/recipes/availability', { signal: controller.signal })
      .then((results) => {
        if (!controller.signal.aborted) setAvailability(Object.fromEntries(results.map((entry) => [entry.recipe_id, entry])))
      })
      .catch(() => { if (!controller.signal.aborted) setAvailability({}) })
    return () => controller.abort()
  }, [page, refresh])

  useEffect(() => {
    if (initialRecipeId === undefined) return
    const controller = new AbortController()
    getRecipe(initialRecipeId, controller.signal)
      .then((recipe) => { if (!controller.signal.aborted) setView({ page: 'detail', recipe }) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => controller.abort()
  }, [initialRecipeId])

  function navigate(next: View) { setError(''); setView(next) }

  async function openRecipe(id: number) {
    setBusy(true)
    setError('')
    try { navigate({ page: 'detail', recipe: await getRecipe(id) }) }
    catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }

  async function removeRecipe(recipe: Recipe) {
    if (!window.confirm('¿Eliminar “' + recipe.name + '”? Esta acción no se puede deshacer.')) return
    setBusy(true)
    setError('')
    try { await deleteRecipe(recipe.id); navigate({ page: 'list' }) }
    catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }

  function recipeBadge(id: number) {
    const result = availability[id]
    return result && <StatusBadge tone={result.classification === 'ready_to_cook' ? 'success' : 'warning'}>{classifications[result.classification]}</StatusBadge>
  }

  return (
    <>
      {page === 'list' && (
        <>
          <PageHeader title="Recetas" description="Tus platos, ingredientes y pasos de preparación.">
            <button disabled={busy} onClick={() => navigate({ page: 'create' })}><Icon name="plus" />Nueva receta</button>
          </PageHeader>
          <label className="search">Buscar por nombre
            <input type="search" placeholder="Por ejemplo, arroz con verduras" value={query} disabled={busy}
              onChange={(event) => setQuery(event.target.value)} />
          </label>
          {(loading || busy) && <LoadingState text={busy ? 'Abriendo receta…' : 'Cargando recetas…'} />}
          {error && <ErrorState message={error} onRetry={() => setRefresh((count) => count + 1)} />}
          {!loading && !error && (recipes.length ? (
            <ul className="recipes">
              {recipes.map((recipe) => (
                <li className="panel" key={recipe.id}>
                  <h2 className="recipe-card-title"><button className="text-button" disabled={busy} onClick={() => openRecipe(recipe.id)}>{recipe.name}</button></h2>
                  {recipe.description && <p className="description">{recipe.description}</p>}
                  <p className="recipe-meta"><span><Icon name="clock" />{recipe.preparation_minutes} min</span>
                    <span><Icon name="people" />{recipe.servings} {recipe.servings === 1 ? 'ración' : 'raciones'}</span></p>
                  {recipeBadge(recipe.id)}
                </li>
              ))}
            </ul>
          ) : <EmptyState title={query.trim() ? 'No hay recetas con ese nombre' : 'Guarda tu primera receta'}>
            {query.trim() ? 'Prueba con otro nombre.' : 'Añade sus ingredientes y pasos para tenerla siempre a mano.'}
          </EmptyState>)}
        </>
      )}
      {view.page === 'detail' && (
        <>
          <button className="text-button back" disabled={busy} onClick={() => navigate({ page: 'list' })}>← Todas las recetas</button>
          <PageHeader title={view.recipe.name} description={view.recipe.preparation_minutes + ' min · ' + view.recipe.servings + (view.recipe.servings === 1 ? ' ración' : ' raciones')}>
            <button className="secondary" disabled={busy} onClick={() => navigate({ page: 'edit', recipe: view.recipe })}>Editar receta</button>
            <button className="danger" disabled={busy} onClick={() => removeRecipe(view.recipe)}>{busy ? 'Eliminando…' : 'Eliminar receta'}</button>
          </PageHeader>
          {error && <ErrorState message={error} />}
          <article className="panel detail">
            <div className="badges">{recipeBadge(view.recipe.id)}</div>
            {view.recipe.description && <p className="preserve-lines">{view.recipe.description}</p>}
            <h2>Ingredientes</h2>
            <ul className="ingredients">{view.recipe.ingredients.map((ingredient, index) => (
              <li key={index}><span>{ingredient.name}</span><span>{amount(String(ingredient.quantity), ingredient.unit)}</span></li>
            ))}</ul>
            <h2>Preparación</h2><p className="preserve-lines">{view.recipe.instructions}</p>
            <p className="muted timestamps">Creada el {dateFormat.format(new Date(view.recipe.created_at))}<br />
              Actualizada el {dateFormat.format(new Date(view.recipe.updated_at))}</p>
          </article>
        </>
      )}
      {(view.page === 'create' || view.page === 'edit') && (
        <>
          <PageHeader title={view.page === 'create' ? 'Nueva receta' : 'Editar receta'} description="Ingredientes claros y pasos fáciles de seguir." />
          <RecipeForm recipe={view.page === 'edit' ? view.recipe : undefined}
            onSave={(recipe) => navigate({ page: 'detail', recipe })}
            onCancel={() => navigate(view.page === 'edit' ? { page: 'detail', recipe: view.recipe } : { page: 'list' })} />
        </>
      )}
    </>
  )
}
