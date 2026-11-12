import { useState, type FormEvent } from 'react'
import { unitLabel } from './format'
import { errorMessage, saveRecipe, units, type Recipe, type Unit } from './api'

interface IngredientRow {
  key: string
  name: string
  quantity: string
  unit: Unit
}

function newIngredient(): IngredientRow {
  return { key: crypto.randomUUID(), name: '', quantity: '', unit: 'g' }
}

export default function RecipeForm({ recipe, onSave, onCancel }: {
  recipe?: Recipe
  onSave: (recipe: Recipe) => void
  onCancel: () => void
}) {
  const [ingredients, setIngredients] = useState<IngredientRow[]>(() =>
    recipe?.ingredients.map((ingredient) => ({
      ...ingredient,
      key: crypto.randomUUID(),
      quantity: String(ingredient.quantity),
    })) ?? [newIngredient()],
  )
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function updateIngredient(key: string, change: Partial<IngredientRow>) {
    setIngredients((rows) => rows.map((row) => row.key === key ? { ...row, ...change } : row))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const name = String(fields.get('name')).trim()
    const instructions = String(fields.get('instructions')).trim()
    if (!name || !instructions || ingredients.some((row) => !row.name.trim())) {
      setError('Escribe el nombre de la receta, de cada ingrediente y los pasos de preparación.')
      return
    }

    setSaving(true)
    setError('')
    try {
      const saved = await saveRecipe({
        name,
        description: String(fields.get('description')).trim() || null,
        preparation_minutes: Number(fields.get('preparation_minutes')),
        servings: Number(fields.get('servings')),
        ingredients: ingredients.map((row) => ({
          name: row.name.trim(), quantity: Number(row.quantity), unit: row.unit,
        })),
        instructions,
      }, recipe?.id)
      onSave(saved)
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel recipe-form" onSubmit={handleSubmit}>
      <fieldset disabled={saving}>
        <legend>Datos de la receta</legend>
        <label>Nombre
          <input name="name" required maxLength={120} defaultValue={recipe?.name} />
        </label>
        <label>Descripción <span className="muted">(opcional)</span>
          <textarea name="description" rows={2} maxLength={2000} defaultValue={recipe?.description ?? ''} />
        </label>
        <div className="pair">
          <label>Tiempo de preparación (min)
            <input name="preparation_minutes" type="number" required min={0} max={9999999} defaultValue={recipe?.preparation_minutes} />
          </label>
          <label>Raciones
            <input name="servings" type="number" required min={1} max={9999999} defaultValue={recipe?.servings ?? 1} />
          </label>
        </div>
      </fieldset>
      <fieldset disabled={saving}>
        <legend>Ingredientes</legend>
        {ingredients.map((row, index) => (
          <div className="ingredient-row" key={row.key}>
            <label className="ingredient-name">Ingrediente {index + 1}
              <input required maxLength={120} value={row.name}
                onChange={(event) => updateIngredient(row.key, { name: event.target.value })} />
            </label>
            <label>Cantidad
              <input type="number" required min="0" step="any" value={row.quantity}
                onChange={(event) => {
                  const input = event.currentTarget
                  input.setCustomValidity(input.valueAsNumber <= 0 ? 'Introduce una cantidad mayor que cero.' : '')
                  updateIngredient(row.key, { quantity: input.value })
                }} />
            </label>
            <label>Unidad
              <select value={row.unit} onChange={(event) => updateIngredient(row.key, { unit: event.target.value as Unit })}>
                {units.map((unit) => <option key={unit} value={unit}>{unitLabel(unit)}</option>)}
              </select>
            </label>
            <button className="secondary" type="button" disabled={ingredients.length === 1}
              aria-label={'Quitar ingrediente ' + (index + 1)}
              onClick={() => setIngredients((rows) => rows.filter((item) => item.key !== row.key))}>Quitar</button>
          </div>
        ))}
        <button className="secondary" type="button" onClick={() => setIngredients((rows) => [...rows, newIngredient()])}>
          Añadir ingrediente
        </button>
      </fieldset>
      <fieldset disabled={saving}>
        <legend>Preparación</legend>
        <label>Instrucciones
          <textarea name="instructions" required rows={6} maxLength={20000} defaultValue={recipe?.instructions} />
        </label>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Guardar receta'}</button>
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  )
}
