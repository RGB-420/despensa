import { useEffect, useState } from 'react'
import { errorMessage, request } from './api'
import { amount } from './format'
import { PageHeader, Icon } from './ui'
import { ItemForm, ListForm, TransferForm, jsonOptions } from './ShoppingForms'
import type { ShoppingItem, ShoppingList } from './shoppingTypes'

type Editor = { type: 'manual'; item: ShoppingItem | null }
  | { type: 'purchase' | 'transfer'; item: ShoppingItem }

export default function Shopping({ initialCreate = false, initialListId, initialFilter = 'all' }: {
  initialCreate?: boolean; initialListId?: number; initialFilter?: 'pending' | 'all'
}) {
  const [lists, setLists] = useState<ShoppingList[]>([])
  const [current, setCurrent] = useState<ShoppingList | null>(null)
  const [mode, setMode] = useState<'lists' | 'detail' | 'settings'>(initialCreate ? 'settings' : initialListId ? 'detail' : 'lists')
  const [editor, setEditor] = useState<Editor | null>(null)
  const [filter, setFilter] = useState<string>(initialFilter)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(Boolean(initialListId))
  const [error, setError] = useState('')

  useEffect(() => {
    if (mode !== 'lists') return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    request<ShoppingList[]>('/shopping-lists', { signal: controller.signal })
      .then((results) => { if (!controller.signal.aborted) setLists(results) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [mode, refresh])


  useEffect(() => {
    if (initialListId === undefined) return
    const controller = new AbortController()
    request<ShoppingList>('/shopping-lists/' + initialListId, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) saved(result) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => controller.abort()
  }, [initialListId])

  function saved(result: ShoppingList) {
    setCurrent(result)
    setMode('detail')
    setEditor(null)
    setError('')
  }

  async function act(path: string, options?: RequestInit) {
    setBusy(true)
    setError('')
    try { saved(await request<ShoppingList>(path, options)) }
    catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }

  async function removeList(list: ShoppingList) {
    if (!window.confirm('¿Eliminar “' + list.name + '” y su registro de compra? Los productos añadidos a la despensa se conservan.')) return
    setBusy(true)
    setError('')
    try {
      await request<void>('/shopping-lists/' + list.id, { method: 'DELETE' })
      setCurrent(null)
      setMode('lists')
      setRefresh((value) => value + 1)
    } catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }

  function removeItem(item: ShoppingItem) {
    const explanation = item.source === 'calculated' ? ' Volverá a generarse si recalculas y sigue faltando.' : ''
    if (window.confirm('¿Quitar “' + item.name + '” de la lista?' + explanation)) {
      void act('/shopping-lists/' + current!.id + '/items/' + item.id, { method: 'DELETE' })
    }
  }

  if (mode === 'settings') {
    return <><PageHeader title={current ? 'Editar lista de compra' : 'Nueva lista de compra'} description="Reúne los ingredientes de tus recetas y añade lo que necesites." />
      <ListForm list={current} onSave={saved} onCancel={() => setMode(current ? 'detail' : 'lists')} /></>
  }
  if (current && editor) {
    const actions = { list: current, onSave: saved, onCancel: () => setEditor(null) }
    if (editor.type === 'transfer') return <TransferForm {...actions} item={editor.item} />
    return <ItemForm {...actions} item={editor.item} purchase={editor.type === 'purchase'} />
  }

  const base = current ? '/shopping-lists/' + current.id : ''
  const visibleItems = current?.items.filter((item) =>
    filter === 'all' || (filter === 'pending' ? !item.purchased_at : Boolean(item.purchased_at)),
  ) ?? []

  return (
    <>
      <div className="heading">
        <div><h1>{mode === 'detail' && current ? current.name : 'Lista de la compra'}</h1>
          <p className="muted">De tus recetas a la compra y de la compra a tu despensa.</p></div>
        {mode === 'lists'
          ? <button disabled={busy} onClick={() => { setCurrent(null); setMode('settings') }}><Icon name="plus" />Nueva lista</button>
          : <button className="secondary" disabled={busy} onClick={() => { setCurrent(null); setMode('lists') }}>← Todas las listas</button>}
      </div>
      {error && <div className="error" role="alert"><p>{error}</p>
        <button className="secondary" disabled={busy} onClick={() => {
          if (current) void act(base)
          else if (initialListId) void act('/shopping-lists/' + initialListId)
          else setRefresh((value) => value + 1)
        }}>Reintentar</button>
      </div>}
      {busy && <p role="status">Actualizando lista…</p>}
      {mode === 'lists' && (
        <>
          {loading && <p role="status">Cargando listas…</p>}
          {!loading && !error && (lists.length ? (
            <ul className="recipes">
              {lists.map((list) => (
                <li className="panel" key={list.id}>
                  <h2><button className="text-button" disabled={busy} onClick={() => act('/shopping-lists/' + list.id)}>{list.name}</button></h2>
                  <p>{list.pending_count} pendientes · {list.purchased_count} comprados</p>
                  <p className="muted">{list.transferred_count} añadidos a la despensa</p>
                  <span className="badge">{list.is_complete ? 'Compra completada' : list.items.length ? 'En curso' : 'Lista vacía'}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="panel empty"><h2>Tu próxima compra empieza aquí</h2><p>Selecciona recetas o añade tus productos habituales.</p></div>
          ))}
        </>
      )}
      {mode === 'detail' && current && (
        <>
          <div className="panel shopping-overview">
            <p><strong>{current.purchased_count} de {current.items.length} productos comprados</strong>
              {' · '}{current.transferred_count} añadidos a mi despensa</p>
            <progress aria-label="Progreso de compra" value={current.purchased_count} max={current.items.length || 1} />
            <div className="actions">
              <button className="secondary" disabled={busy} onClick={() => setMode('settings')}>Editar lista y recetas</button>
              <button className="secondary" disabled={busy} onClick={() => act(base + '/recalculate', { method: 'POST' })}>Recalcular necesidades</button>
              <button disabled={busy} onClick={() => setEditor({ type: 'manual', item: null })}>Añadir producto manual</button>
              <button className="danger" disabled={busy} onClick={() => removeList(current)}>Eliminar lista</button>
            </div>
          </div>
          <section className="panel shopping-overview" aria-label="Recetas seleccionadas">
            <h2>Recetas seleccionadas</h2>
            {current.selected_recipes.length
              ? <ul>{current.selected_recipes.map((entry) => <li key={entry.recipe_id}>{entry.name} · {entry.servings} {entry.servings === 1 ? 'ración' : 'raciones'}</li>)}</ul>
              : <p className="muted">Esta lista contiene productos añadidos manualmente.</p>}
            {current.requirements.length > 0 && (
              <details><summary>Ver cálculo conjunto de ingredientes</summary>
                <ul className="availability-ingredients">
                  {current.requirements.map((requirement, index) => (
                    <li key={index}>
                      <strong>{requirement.name}</strong>
                      <p>Necesitas {amount(requirement.required_quantity, requirement.unit)}
                        {' · '}En despensa {amount(requirement.available_quantity, requirement.unit)}
                        {' · '}Comprado sin transferir {amount(requirement.purchased_quantity, requirement.unit)}
                        {' · '}Faltan {amount(requirement.shortfall_quantity, requirement.unit)}</p>
                      {requirement.warning && <p className="warning">{requirement.warning}</p>}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
          <label className="search">Mostrar productos
            <select value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="all">Todos</option><option value="pending">Pendientes</option><option value="purchased">Comprados</option>
            </select>
          </label>
          {(['pending', 'purchased'] as const).map((group) => {
            const items = visibleItems.filter((item) => group === 'pending' ? !item.purchased_at : Boolean(item.purchased_at))
            if (!items.length) return null
            return (
              <section className="shopping-group" key={group} aria-label={group === 'pending' ? 'Productos pendientes' : 'Productos comprados'}>
                <h2>{group === 'pending' ? 'Pendientes' : 'Comprados'}</h2>
                <ul className="shopping-items">
                  {items.map((item) => (
                    <li className="panel shopping-item" key={item.id}>
                      <div>
                        <h3>{item.name}</h3>
                        <p>{amount(item.quantity, item.unit)}
                          {' · '}<span className="muted">{item.source === 'manual' ? 'Añadido a mano' : 'Calculado de recetas'}</span></p>
                        {item.purchased_at && <p>Comprado {amount(item.purchased_quantity!, item.purchased_unit!)}
                          {' · '}Caducidad {item.expiration_date ?? 'sin fecha'}</p>}
                        <span className={'badge ' + (!item.purchased_at ? 'warning' : '')}>
                          {item.transferred_at ? 'Añadido a mi despensa' : item.purchased_at ? 'Comprado · pendiente de guardar' : 'Pendiente de compra'}
                        </span>
                      </div>
                      <div className="actions">
                        {!item.purchased_at && <>
                          <button disabled={busy} onClick={() => setEditor({ type: 'purchase', item })} aria-label={'Registrar compra de ' + item.name}>Registrar compra</button>
                          {item.source === 'manual' && <button className="secondary" disabled={busy}
                            onClick={() => setEditor({ type: 'manual', item })}>Editar {item.name}</button>}
                          <button className="danger" disabled={busy} onClick={() => removeItem(item)}>Quitar {item.name}</button>
                        </>}
                        {item.purchased_at && !item.transferred_at && <>
                          <button disabled={busy} onClick={() => setEditor({ type: 'transfer', item })}>Añadir a mi despensa</button>
                          <button className="secondary" disabled={busy} onClick={() => setEditor({ type: 'purchase', item })} aria-label={'Modificar compra de ' + item.name}>Modificar compra</button>
                          <button className="secondary" disabled={busy} onClick={() => act(base + '/items/' + item.id + '/purchase', jsonOptions('PUT', { purchased: false }))}>Desmarcar {item.name}</button>
                        </>}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )
          })}
          {!visibleItems.length && <div className="panel empty"><h2>No hay productos pendientes en esta vista</h2>
            <p>Añade productos, selecciona recetas o cambia el filtro.</p>
            {current.purchased_count > 0 && <button className="secondary" onClick={() => setFilter('purchased')}>Ver productos comprados</button>}
          </div>}
        </>
      )}
    </>
  )
}
