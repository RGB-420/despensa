export function formatQuantity(value: string) {
  return value.includes('.') && !/[eE]/.test(value) ? value.replace(/0+$/, '').replace(/\.$/, '') : value
}

export function unitLabel(unit: string) {
  return unit === 'unit' ? 'ud.' : unit
}

export function amount(value: string, unit: string) {
  return formatQuantity(value) + ' ' + unitLabel(unit)
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
    .format(new Date(value + 'T12:00:00'))
}
