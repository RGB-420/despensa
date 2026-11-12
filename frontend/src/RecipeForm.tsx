import { useState, type FormEvent } from 'react'
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
      setError('Enter a recipe name, a name for each ingredient, and preparation instructions.')
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
        <legend>Recipe basics</legend>
        <label>Name
          <input name="name" required maxLength={120} defaultValue={recipe?.name} />
        </label>
        <label>Description <span className="muted">(optional)</span>
          <textarea name="description" rows={2} maxLength={2000} defaultValue={recipe?.description ?? ''} />
        </label>
        <div className="pair">
          <label>Preparation time (min)
            <input name="preparation_minutes" type="number" required min={0} max={9999999} defaultValue={recipe?.preparation_minutes} />
          </label>
          <label>Servings
            <input name="servings" type="number" required min={1} max={9999999} defaultValue={recipe?.servings ?? 1} />
          </label>
        </div>
      </fieldset>
      <fieldset disabled={saving}>
        <legend>Ingredients</legend>
        {ingredients.map((row, index) => (
          <div className="ingredient-row" key={row.key}>
            <label className="ingredient-name">Ingredient {index + 1}
              <input required maxLength={120} value={row.name}
                onChange={(event) => updateIngredient(row.key, { name: event.target.value })} />
            </label>
            <label>Quantity
              <input type="number" required min="0" step="any" value={row.quantity}
                onChange={(event) => {
                  const input = event.currentTarget
                  input.setCustomValidity(input.valueAsNumber <= 0 ? 'Enter a quantity greater than zero.' : '')
                  updateIngredient(row.key, { quantity: input.value })
                }} />
            </label>
            <label>Unit
              <select value={row.unit} onChange={(event) => updateIngredient(row.key, { unit: event.target.value as Unit })}>
                {units.map((unit) => <option key={unit}>{unit}</option>)}
              </select>
            </label>
            <button className="secondary" type="button" disabled={ingredients.length === 1}
              aria-label={'Remove ingredient ' + (index + 1)}
              onClick={() => setIngredients((rows) => rows.filter((item) => item.key !== row.key))}>Remove</button>
          </div>
        ))}
        <button className="secondary" type="button" onClick={() => setIngredients((rows) => [...rows, newIngredient()])}>
          Add ingredient
        </button>
      </fieldset>
      <fieldset disabled={saving}>
        <legend>Preparation</legend>
        <label>Instructions
          <textarea name="instructions" required rows={6} maxLength={20000} defaultValue={recipe?.instructions} />
        </label>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save recipe'}</button>
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
