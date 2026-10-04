import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge CSS class names with tailwind-merge and clsx.
 * Core Shadcn/UI styling utility.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
