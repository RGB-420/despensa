import type { Unit } from './api'

export interface ShoppingItem {
  id: number
  list_id: number
  source: 'calculated' | 'manual'
  name: string
  quantity: string
  unit: Unit
  purchased_at: string | null
  purchased_quantity: string | null
  purchased_unit: Unit | null
  expiration_date: string | null
  transferred_at: string | null
  inventory_item_id: number | null
}

export interface ShoppingRequirement {
  name: string
  unit: Unit
  required_quantity: string
  available_quantity: string
  purchased_quantity: string
  shortfall_quantity: string
  warning: string | null
}

export interface ShoppingList {
  id: number
  name: string
  selected_recipes: { recipe_id: number; name: string; servings: number }[]
  requirements: ShoppingRequirement[]
  items: ShoppingItem[]
  pending_count: number
  purchased_count: number
  transferred_count: number
  is_complete: boolean
  created_at: string
  updated_at: string
}
