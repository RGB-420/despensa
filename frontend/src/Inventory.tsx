import { useEffect, useState, type FormEvent } from 'react'
import { amount, formatDate, unitLabel } from './format'
import { PageHeader, LoadingState, Icon } from './ui'
import { errorMessage, request, units, type Unit } from './api'

interface InventoryInput {
  name: string
  quantity: string
  unit: Unit
  expiration_date: string | null
  minimum_stock: string | null
}

export interface InventoryItem extends InventoryInput {
  id: number
  created_at: string
  updated_at: string
  expiration_status: 'expired' | 'expiring_soon' | 'fresh' | 'no_date'
  stock_status: 'out_of_stock' | 'low_stock' | 'in_stock'
}

function InventoryForm({ item, onSave, onCancel }: {
  item: InventoryItem | null
  onSave: () => void
  onCancel: () => void
}) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const name = String(fields.get('name')).trim()
    if (!name) {
      setError('Escribe el nombre del producto.')
      return
    }
    const data: InventoryInput = {
      name,
      quantity: String(fields.get('quantity')),
      unit: String(fields.get('unit')) as Unit,
      expiration_date: String(fields.get('expiration_date')) || null,
      minimum_stock: String(fields.get('minimum_stock')) || null,
    }
    setSaving(true)
    setError('')
    try {
      await request<InventoryItem>(item ? '/inventory/' + item.id : '/inventory', {
        method: item ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      onSave()
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title={item ? 'Editar producto' : 'Añadir producto'} description="Guarda su cantidad y fecha para organizar mejor tu despensa." />
      <form className="panel recipe-form" onSubmit={submit}>
        <fieldset disabled={saving}>
          <legend>Producto o lote</legend>
          <label>Nombre del producto
            <input name="name" required maxLength={120} defaultValue={item?.name} />
          </label>
          <div className="pair">
            <label>Cantidad
              <input name="quantity" type="number" required min={0} step="0.000001"
                max="999999999999.999999" defaultValue={item?.quantity ?? '0'} />
            </label>
            <label>Unidad
              <select name="unit" defaultValue={item?.unit ?? 'g'}>
                {units.map((unit) => <option key={unit} value={unit}>{unitLabel(unit)}</option>)}
              </select>
            </label>
          </div>
          <label>Fecha de caducidad (opcional)
            <input type="date" name="expiration_date" defaultValue={item?.expiration_date ?? ''} />
          </label>
          <label>Existencias mínimas (opcional, en la misma unidad)
            <input type="number" name="minimum_stock" min={0} step="0.000001"
              max="999999999999.999999" defaultValue={item?.minimum_stock ?? ''} />
          </label>
        </fieldset>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="actions">
          <button disabled={saving}>{saving ? 'Guardando…' : 'Guardar producto'}</button>
          <button className="secondary" type="button" disabled={saving} onClick={onCancel}>Cancelar</button>
        </div>
      </form>
    </>
  )
}

export default function Inventory({ initialCreate = false, initialExpiration = 'all', initialStock = 'all' }: {
  initialCreate?: boolean; initialExpiration?: string; initialStock?: string
}) {
  const [mode, setMode] = useState<'list' | 'form'>(initialCreate ? 'form' : 'list')
  const [editing, setEditing] = useState<InventoryItem | null>(null)
  const [items, setItems] = useState<InventoryItem[]>([])
  const [query, setQuery] = useState('')
  const [expiration, setExpiration] = useState(initialExpiration)
  const [stock, setStock] = useState(initialStock)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (mode !== 'list') return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    const parameters = new URLSearchParams({ q: query, expiration, stock })
    request<InventoryItem[]>('/inventory?' + parameters, { signal: controller.signal })
      .then((results) => { if (!controller.signal.aborted) setItems(results) })
      .catch((error) => { if (!controller.signal.aborted) setError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [mode, query, expiration, stock, refresh])

  async function edit(item: InventoryItem) {
    setBusy(true)
    setError('')
    try {
      setEditing(await request<InventoryItem>('/inventory/' + item.id))
      setMode('form')
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function remove(item: InventoryItem) {
    if (!window.confirm('¿Eliminar “' + item.name + '”? Esta acción no se puede deshacer.')) return
    setBusy(true)
    setError('')
    try {
      await request<void>('/inventory/' + item.id, { method: 'DELETE' })
      setRefresh((count) => count + 1)
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (mode === 'form') {
    return <InventoryForm item={editing} onCancel={() => setMode('list')} onSave={() => setMode('list')} />
  }

  return (
    <>
      <PageHeader title="Mi despensa" description="Productos y lotes, con sus cantidades y caducidades.">
        <button disabled={busy} onClick={() => { setEditing(null); setMode('form') }}><Icon name="plus" />Añadir producto</button>
      </PageHeader>
      <div className="filters">
        <label>Buscar producto
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label>Caducidad
          <select value={expiration} onChange={(event) => setExpiration(event.target.value)}>
            <option value="all">Todas las fechas</option>
            <option value="expired">Caducados</option>
            <option value="expiring_soon">Caducan pronto</option>
            <option value="not_expired">Sin caducar</option>
            <option value="no_date">Sin fecha</option>
          </select>
        </label>
        <label>Existencias
          <select value={stock} onChange={(event) => setStock(event.target.value)}>
            <option value="all">Todos los productos</option>
            <option value="in_stock">Con existencias</option>
            <option value="out_of_stock">Agotados</option>
            <option value="low_stock">En el mínimo o por debajo</option>
          </select>
        </label>
      </div>
      <p className="muted">Cada entrada representa un producto o lote. Las cantidades cero indican productos agotados.</p>
      {(loading || busy) && <LoadingState text={busy ? 'Actualizando…' : 'Cargando productos…'} />}
      {error && <div className="error" role="alert"><p>{error}</p>
        <button className="secondary" onClick={() => setRefresh((count) => count + 1)}>Reintentar</button>
      </div>}
      {!loading && !error && (items.length ? (
        <ul className="recipes">
          {items.map((item) => (
            <li className="panel" key={item.id}>
              <h2>{item.name}</h2>
              <p className="quantity">{amount(item.quantity, item.unit)}</p>
              <p className="product-caption">Caducidad {item.expiration_date ? formatDate(item.expiration_date) : 'sin fecha'}</p>
              {item.minimum_stock !== null && <p className="muted">Mínimo {amount(item.minimum_stock, item.unit)}</p>}
              <div className="badges">
                {item.expiration_status === 'expired' && <span className="badge warning">Caducado</span>}
                {item.expiration_status === 'expiring_soon' && <span className="badge warning">Caduca pronto</span>}
                {item.stock_status === 'out_of_stock' && <span className="badge warning">Agotado</span>}
                {item.stock_status === 'low_stock' && <span className="badge warning">Existencias bajas</span>}
              </div>
              <div className="actions">
                <button className="secondary" disabled={busy} onClick={() => edit(item)} aria-label={'Editar ' + item.name}>Editar</button>
                <button className="danger" disabled={busy} onClick={() => remove(item)} aria-label={'Eliminar ' + item.name}>Eliminar</button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="panel empty">
          <h2>{query || expiration !== 'all' || stock !== 'all' ? 'No hay coincidencias' : 'Tu despensa está vacía'}</h2>
          <p className="muted">Añade un producto o ajusta los filtros.</p>
        </div>
      ))}
    </>
  )
}

