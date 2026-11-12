import { useEffect, useState, type FormEvent } from 'react'
import { errorMessage, request, units, type Recipe } from './api'
import type { InventoryItem } from './Inventory'
import { amount, unitLabel } from './format'
import type { ShoppingItem, ShoppingList } from './shoppingTypes'

export function jsonOptions(method: string, data: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }
}

interface FormActions {
  onSave: (list: ShoppingList) => void
  onCancel: () => void
}

export function ListForm({ list, onSave, onCancel }: FormActions & { list: ShoppingList | null }) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [selected, setSelected] = useState<Record<string, string>>(() => Object.fromEntries(
    (list?.selected_recipes ?? []).map((entry) => [String(entry.recipe_id), String(entry.servings)]),
  ))
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    request<Recipe[]>('/recipes', { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setRecipes(data) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = String(new FormData(event.currentTarget).get('name')).trim()
    if (!name) { setError('Escribe el nombre de la lista.'); return }
    setSaving(true)
    setError('')
    try {
      const result = await request<ShoppingList>(list ? '/shopping-lists/' + list.id : '/shopping-lists',
        jsonOptions(list ? 'PUT' : 'POST', {
          name,
          selected_recipes: Object.entries(selected).map(([recipe_id, servings]) => ({
            recipe_id: Number(recipe_id), servings: Number(servings),
          })),
        }))
      onSave(result)
    } catch (error) { setError(errorMessage(error)) }
    finally { setSaving(false) }
  }

  function toggle(id: number, servings: number, checked: boolean) {
    setSelected((current) => {
      const next = { ...current }
      if (checked) next[id] = String(servings)
      else delete next[id]
      return next
    })
  }

  const removed = (list?.selected_recipes ?? []).filter((entry) => !recipes.some((recipe) => recipe.id === entry.recipe_id))
  return (
    <form className="panel recipe-form" onSubmit={submit}>
      <fieldset disabled={saving || loading}>
        <legend>{list ? 'Editar lista y recetas' : 'Nueva lista de compra'}</legend>
        <label>Nombre de la lista<input name="name" required maxLength={120} defaultValue={list?.name} /></label>
        <p className="muted">Selecciona tus recetas y ajusta las raciones. Se descontarán las existencias una sola vez.</p>
        {loading && <p role="status">Cargando recetas…</p>}
        {!loading && !recipes.length && <p>Puedes crear una lista manual y añadir recetas más adelante.</p>}
        <div className="recipe-selection">
          {recipes.map((recipe) => (
            <div className="selection-row" key={recipe.id}>
              <label className="checkbox-label">
                <input type="checkbox" checked={selected[recipe.id] !== undefined}
                  onChange={(event) => toggle(recipe.id, recipe.servings, event.target.checked)} />
                {recipe.name}
              </label>
              {selected[recipe.id] !== undefined && (
                <label>Raciones de {recipe.name}
                  <input type="number" min={1} max={9999999} required value={selected[recipe.id]}
                    onChange={(event) => setSelected((current) => ({ ...current, [recipe.id]: event.target.value }))} />
                </label>
              )}
            </div>
          ))}
          {!loading && removed.map((entry) => (
            <label className="checkbox-label warning" key={entry.recipe_id}>
              <input type="checkbox" checked={selected[entry.recipe_id] !== undefined}
                onChange={(event) => toggle(entry.recipe_id, entry.servings, event.target.checked)} />
              {entry.name} (eliminada, desmárcala para continuar)
            </label>
          ))}
        </div>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button disabled={saving || loading}>{saving ? 'Guardando…' : 'Guardar y calcular'}</button>
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  )
}

export function ItemForm({ list, item, purchase = false, onSave, onCancel }: FormActions & {
  list: ShoppingList
  item: ShoppingItem | null
  purchase?: boolean
}) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const name = String(fields.get('name') ?? '').trim()
    if (!purchase && !name) { setError('Escribe el nombre del producto.'); return }
    const quantity = String(fields.get('quantity'))
    const unit = String(fields.get('unit'))
    const base = '/shopping-lists/' + list.id + '/items'
    setSaving(true)
    setError('')
    try {
      const path = purchase ? base + '/' + item!.id + '/purchase' : item ? base + '/' + item.id : base
      const data = purchase
        ? { purchased: true, quantity, unit, expiration_date: String(fields.get('expiration_date')) || null }
        : { name, quantity, unit }
      onSave(await request<ShoppingList>(path, jsonOptions(purchase || item ? 'PUT' : 'POST', data)))
    } catch (error) { setError(errorMessage(error)) }
    finally { setSaving(false) }
  }

  return (
    <form className="panel recipe-form" onSubmit={submit}>
      <fieldset disabled={saving}>
        <legend>{purchase ? 'Registrar compra de ' + item!.name : item ? 'Editar producto manual' : 'Añadir producto manual'}</legend>
        {purchase
          ? <p className="muted">Indica lo que has comprado realmente. Después podrás añadirlo a tu despensa.</p>
          : <label>Nombre del producto<input name="name" required maxLength={120} defaultValue={item?.name} /></label>}
        <div className="pair">
          <label>{purchase ? 'Cantidad comprada' : 'Cantidad'}
            <input type="number" name="quantity" min="0.000001" max="999999999999.999999" step="0.000001"
              required defaultValue={purchase ? item?.purchased_quantity ?? item?.quantity : item?.quantity ?? '1'} />
          </label>
          <label>Unidad
            <select name="unit" defaultValue={purchase ? item?.purchased_unit ?? item?.unit : item?.unit ?? 'unit'}>
              {units.map((unit) => <option key={unit} value={unit}>{unitLabel(unit)}</option>)}
            </select>
          </label>
        </div>
        {purchase && <label>Fecha de caducidad (opcional)
          <input name="expiration_date" type="date" defaultValue={item?.expiration_date ?? ''} />
        </label>}
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button disabled={saving}>{saving ? 'Guardando…' : purchase ? 'Confirmar compra' : 'Guardar producto manual'}</button>
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  )
}

export function TransferForm({ list, item, onSave, onCancel }: FormActions & {
  list: ShoppingList
  item: ShoppingItem
}) {
  const [options, setOptions] = useState<InventoryItem[]>([])
  const [target, setTarget] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const path = '/shopping-lists/' + list.id + '/items/' + item.id + '/transfer'

  useEffect(() => {
    const controller = new AbortController()
    request<InventoryItem[]>(path + '-options', { signal: controller.signal })
      .then((results) => {
        if (!controller.signal.aborted) { setOptions(results); setTarget(results.length ? '' : 'new') }
      })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [path])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const data = target === 'new' ? { create_new_batch: true } : { inventory_item_id: Number(target) }
      onSave(await request<ShoppingList>(path, jsonOptions('POST', data)))
    } catch (error) { setError(errorMessage(error)) }
    finally { setSaving(false) }
  }

  return (
    <form className="panel recipe-form" onSubmit={submit}>
      <fieldset disabled={saving || loading}>
        <legend>Añadir a mi despensa</legend>
        <p><strong>{item.name}</strong> · {amount(item.purchased_quantity!, item.purchased_unit!)}</p>
        <p>Caducidad {item.expiration_date ?? 'sin fecha'}</p>
        <p className="muted">Confirma dónde guardar esta compra. Solo se añadirá una vez.</p>
        {loading && <p role="status">Buscando lotes compatibles…</p>}
        <label>Destino de la compra
          <select required value={target} onChange={(event) => setTarget(event.target.value)}>
            <option value="">Elige un destino</option>
            <option value="new">Crear un lote nuevo</option>
            {options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name} · {amount(option.quantity, option.unit)} · {option.expiration_date ?? 'sin fecha'} · Lote {option.id}
              </option>
            ))}
          </select>
        </label>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button disabled={saving || loading || !target}>{saving ? 'Añadiendo…' : 'Confirmar y añadir a mi despensa'}</button>
        <button type="button" className="secondary" disabled={saving} onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  )
}
