import { useEffect, useState } from 'react'
import { errorMessage, request } from './api'
import { amount, formatQuantity } from './format'
import { PageHeader, LoadingState } from './ui'

type Classification = 'ready_to_cook' | 'almost_ready' | 'missing_ingredients'

interface IngredientAvailability {
  name: string
  unit: string
  required_quantity: string
  available_quantity: string
  shortfall_quantity: string
  status: 'available' | 'partial' | 'missing'
}

export interface RecipeAvailability {
  recipe_id: number
  recipe_name: string
  preparation_minutes: number
  servings: number
  evaluated_on: string
  classification: Classification
  availability_percentage: string
  total_ingredients: number
  available_count: number
  partial_count: number
  missing_count: number
  shortfall_count: number
  available_ingredients: IngredientAvailability[]
  missing_or_insufficient_ingredients: IngredientAvailability[]
}

export const classifications: Record<Classification, string> = {
  ready_to_cook: 'Lista para cocinar',
  almost_ready: 'Casi lista',
  missing_ingredients: 'Faltan ingredientes',
}

function IngredientList({ ingredients }: { ingredients: IngredientAvailability[] }) {
  return (
    <ul className="availability-ingredients">
      {ingredients.map((ingredient, index) => (
        <li key={index}>
          <h3>{ingredient.name}</h3>
          <p>
            Necesitas {amount(ingredient.required_quantity, ingredient.unit)}
            {' · '}Disponible {amount(ingredient.available_quantity, ingredient.unit)}
          </p>
          {ingredient.status === 'available'
            ? <span className="badge">Cantidad suficiente</span>
            : <span className="badge warning">
              Faltan {amount(ingredient.shortfall_quantity, ingredient.unit)}
              {ingredient.status === 'partial' ? ' · Hay parte de la cantidad' : ' · Sin existencias utilizables'}
            </span>}
        </li>
      ))}
    </ul>
  )
}

export default function Availability() {
  const [recipes, setRecipes] = useState<RecipeAvailability[]>([])
  const [selected, setSelected] = useState<RecipeAvailability | null>(null)
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('availability')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    request<RecipeAvailability[]>('/recipes/availability', { signal: controller.signal })
      .then((results) => { if (!controller.signal.aborted) setRecipes(results) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [refresh])

  const visibleRecipes = recipes
    .filter((recipe) => filter === 'all' || recipe.classification === filter)
    .sort((first, second) => {
      if (sort === 'shortfalls') {
        return first.shortfall_count - second.shortfall_count
          || Number(second.availability_percentage) - Number(first.availability_percentage)
          || first.recipe_id - second.recipe_id
      }
      if (sort === 'time') {
        return first.preparation_minutes - second.preparation_minutes
          || Number(second.availability_percentage) - Number(first.availability_percentage)
          || first.recipe_id - second.recipe_id
      }
      return Number(second.availability_percentage) - Number(first.availability_percentage)
        || first.shortfall_count - second.shortfall_count
        || first.recipe_id - second.recipe_id
    })

  if (selected) {
    return (
      <>
        <button className="text-button back" onClick={() => setSelected(null)}>← Todas las disponibilidades</button>
        <div className="heading">
          <div>
            <h1>{selected.recipe_name}</h1>
            <p className="muted">{selected.preparation_minutes} min · {selected.servings} {selected.servings === 1 ? 'ración' : 'raciones'}</p>
          </div>
          <span className={'badge ' + (selected.classification === 'ready_to_cook' ? '' : 'warning')}>
            {classifications[selected.classification]}
          </span>
        </div>
        <article className="panel detail">
          <p><strong>{formatQuantity(selected.availability_percentage)} %</strong>
            {' · '}{selected.available_count} de {selected.total_ingredients} {selected.total_ingredients === 1 ? 'ingrediente' : 'ingredientes'} en cantidad suficiente.
          </p>
          <p className="muted">Cálculo del {selected.evaluated_on}. Se excluyen productos caducados y agotados.</p>
          {selected.total_ingredients === 0 && <p>Esta receta no tiene ingredientes registrados. Añádelos en Recetas para calcular su disponibilidad.</p>}
          <h2>Ingredientes disponibles</h2>
          {selected.available_ingredients.length
            ? <IngredientList ingredients={selected.available_ingredients} />
            : <p>No hay ingredientes en cantidad suficiente.</p>}
          <h2>Ingredientes que faltan o son insuficientes</h2>
          {selected.missing_or_insufficient_ingredients.length
            ? <IngredientList ingredients={selected.missing_or_insufficient_ingredients} />
            : <p>No falta ningún ingrediente registrado.</p>}
          <p className="muted">Las cantidades se muestran en gramos, mililitros o unidades. Las entradas equivalentes se agrupan. Consultar esta receta conserva las existencias.</p>
        </article>
      </>
    )
  }

  return (
    <>
      <PageHeader title="¿Qué puedo cocinar?" description="Descubre qué recetas tienen los ingredientes que necesitas.">
        <button className="secondary" disabled={loading} onClick={() => setRefresh((count) => count + 1)}>Actualizar disponibilidad</button>
      </PageHeader>
      <div className="filters">
        <label>Disponibilidad
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">Todas las recetas</option>
            {Object.entries(classifications).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
          </select>
        </label>
        <label>Ordenar por
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="availability">Mayor disponibilidad</option>
            <option value="shortfalls">Menos ingredientes pendientes</option>
            <option value="time">Menor tiempo de preparación</option>
          </select>
        </label>
      </div>
      <p className="notice">El porcentaje indica cuántos ingredientes tienen cantidad suficiente. Una receta está casi lista si solo falta o es insuficiente un ingrediente y al menos otro está disponible.</p>
      {loading && <LoadingState text="Calculando disponibilidad…" />}
      {error && <p className="error" role="alert">{error} Puedes reintentar con «Actualizar disponibilidad».</p>}
      {!loading && !error && (visibleRecipes.length ? (
        <ul className="recipes">
          {visibleRecipes.map((recipe) => (
            <li className="panel" key={recipe.recipe_id}>
              <h2><button className="text-button" onClick={() => setSelected(recipe)}>{recipe.recipe_name}</button></h2>
              <p className="muted">{recipe.preparation_minutes} min · {recipe.servings} {recipe.servings === 1 ? 'ración' : 'raciones'}</p>
              <p><strong>{formatQuantity(recipe.availability_percentage)} %</strong>
                {' · '}{recipe.available_count} de {recipe.total_ingredients} {recipe.total_ingredients === 1 ? 'ingrediente suficiente' : 'ingredientes suficientes'}
              </p>
              <p><span className={'badge ' + (recipe.classification === 'ready_to_cook' ? '' : 'warning')}>
                {classifications[recipe.classification]}
              </span></p>
              {recipe.total_ingredients === 0 && <p>Registra los ingredientes para calcular su disponibilidad.</p>}
              {recipe.missing_or_insufficient_ingredients.length > 0 && (
                <ul className="shortfall-summary">
                  {recipe.missing_or_insufficient_ingredients.map((ingredient, index) => (
                    <li key={index}>Faltan {amount(ingredient.shortfall_quantity, ingredient.unit)} de {ingredient.name}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="panel empty">
          <h2>{recipes.length ? 'No hay recetas con este estado' : 'Todavía no hay recetas'}</h2>
          <p className="muted">Añade recetas en Recetas o cambia el filtro de disponibilidad.</p>
        </div>
      ))}
    </>
  )
}
