import { useEffect, useState } from 'react'
import { deleteRecipe, errorMessage, getRecipe, listRecipes, type Recipe } from './api'
import RecipeForm from './RecipeForm'

type View =
  | { page: 'list' | 'create' }
  | { page: 'detail' | 'edit'; recipe: Recipe }

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function App() {
  const [view, setView] = useState<View>({ page: 'list' })
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [query, setQuery] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
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

  function navigate(next: View) {
    setError('')
    setView(next)
  }

  async function openRecipe(id: number) {
    setBusy(true)
    setError('')
    try {
      navigate({ page: 'detail', recipe: await getRecipe(id) })
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function removeRecipe(recipe: Recipe) {
    if (!window.confirm('Delete “' + recipe.name + '”? This cannot be undone.')) return
    setBusy(true)
    setError('')
    try {
      await deleteRecipe(recipe.id)
      navigate({ page: 'list' })
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <header className="site-header">
        <div className="shell">
          <span className="brand">PantryLab</span>
          <span className="muted">Recipe notebook</span>
        </div>
      </header>
      <main className="shell">
        {page === 'list' && (
          <>
            <div className="heading">
              <div><h1>Recipes</h1><p className="muted">Keep the recipes you cook in one place.</p></div>
              <button disabled={busy} onClick={() => navigate({ page: 'create' })}>New recipe</button>
            </div>
            <label className="search">Search by name
              <input type="search" placeholder="e.g. Lemon rice" value={query} disabled={busy}
                onChange={(event) => setQuery(event.target.value)} />
            </label>
            {(loading || busy) && <p role="status">{busy ? 'Opening recipe…' : 'Loading recipes…'}</p>}
            {error && (
              <div className="error" role="alert">
                <p>{error}</p>
                <button className="secondary" onClick={() => setRefresh((count) => count + 1)}>Reload recipes</button>
              </div>
            )}
            {!loading && !error && (recipes.length ? (
              <ul className="recipes">
                {recipes.map((recipe) => (
                  <li className="panel" key={recipe.id}>
                    <h2><button className="text-button" disabled={busy} onClick={() => openRecipe(recipe.id)}>{recipe.name}</button></h2>
                    {recipe.description && <p className="description">{recipe.description}</p>}
                    <p className="muted">{recipe.preparation_minutes} min · {recipe.servings} servings</p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="panel empty">
                <h2>{query.trim() ? 'No matching recipes' : 'No recipes yet'}</h2>
                <p className="muted">{query.trim() ? 'Try another recipe name.' : 'Add your first recipe to start your notebook.'}</p>
              </div>
            ))}
          </>
        )}
        {view.page === 'detail' && (
          <>
            <button className="text-button back" disabled={busy} onClick={() => navigate({ page: 'list' })}>← All recipes</button>
            <div className="heading">
              <div><h1>{view.recipe.name}</h1><p className="muted">{view.recipe.preparation_minutes} min · {view.recipe.servings} servings</p></div>
              <div className="actions">
                <button className="secondary" disabled={busy} onClick={() => navigate({ page: 'edit', recipe: view.recipe })}>Edit recipe</button>
                <button className="danger" disabled={busy} onClick={() => removeRecipe(view.recipe)}>{busy ? 'Deleting…' : 'Delete'}</button>
              </div>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
            <article className="panel detail">
              {view.recipe.description && <p className="preserve-lines">{view.recipe.description}</p>}
              <h2>Ingredients</h2>
              <ul className="ingredients">
                {view.recipe.ingredients.map((ingredient, index) => (
                  <li key={index}><span>{ingredient.name}</span><span>{ingredient.quantity} {ingredient.unit}</span></li>
                ))}
              </ul>
              <h2>Preparation</h2>
              <p className="preserve-lines">{view.recipe.instructions}</p>
              <p className="muted timestamps">
                Created {dateFormat.format(new Date(view.recipe.created_at))}<br />
                Updated {dateFormat.format(new Date(view.recipe.updated_at))}
              </p>
            </article>
          </>
        )}
        {(view.page === 'create' || view.page === 'edit') && (
          <>
            <h1>{view.page === 'create' ? 'New recipe' : 'Edit recipe'}</h1>
            <RecipeForm recipe={view.page === 'edit' ? view.recipe : undefined}
              onSave={(recipe) => navigate({ page: 'detail', recipe })}
              onCancel={() => navigate(view.page === 'edit' ? { page: 'detail', recipe: view.recipe } : { page: 'list' })} />
          </>
        )}
      </main>
    </>
  )
}
