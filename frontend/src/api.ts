export const units = ['g', 'kg', 'ml', 'l', 'unit'] as const
export type Unit = (typeof units)[number]

export interface Ingredient {
  name: string
  quantity: number
  unit: Unit
}

export interface RecipeInput {
  name: string
  description: string | null
  preparation_minutes: number
  servings: number
  ingredients: Ingredient[]
  instructions: string
}

export interface Recipe extends RecipeInput {
  id: number
  created_at: string
  updated_at: string
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch('/api' + path, options)
  } catch (error) {
    if (options?.signal?.aborted) throw error
    throw new Error('No se ha podido conectar con Despensa. Comprueba que la aplicación esté en marcha.')
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (typeof body?.detail?.message === 'string') throw new Error(body.detail.message)
    if (typeof body?.detail === 'string') throw new Error(body.detail)
    if (response.status === 422) {
      throw new Error('Revisa los campos y los valores introducidos.')
    }
    throw new Error('Despensa no ha podido completar la acción. Vuelve a intentarlo.')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const listRecipes = (query: string, signal: AbortSignal) =>
  request<Recipe[]>('/recipes?' + new URLSearchParams({ q: query }), { signal })

export const getRecipe = (id: number, signal?: AbortSignal) => request<Recipe>('/recipes/' + id, { signal })

export function saveRecipe(data: RecipeInput, id?: number) {
  return request<Recipe>(id === undefined ? '/recipes' : '/recipes/' + id, {
    method: id === undefined ? 'POST' : 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export const deleteRecipe = (id: number) =>
  request<void>('/recipes/' + id, { method: 'DELETE' })

export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'No se ha podido completar la acción. Vuelve a intentarlo.'
