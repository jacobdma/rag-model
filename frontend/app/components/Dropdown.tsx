"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"

type Option = {
  label: string
  value: string
}

interface DropdownProps {
  options: Option[]
  value: string
  onChange: (value: string) => void
  label?: string
}

export default function Dropdown({ options, value, onChange, label }: DropdownProps) {
  const [open, setOpen] = useState(false)
  const selected = options.find((o) => o.value === value)

  return (
    <div className="relative">
      {label && (
        <label className="block px-3 pb-2 text-responsive-sm font-medium text-neutral-700 dark:text-neutral-300">
          {label}
        </label>
      )}
      <button
        onClick={() => setOpen(!open)}
        className="
          w-full h-9 flex justify-between items-center
          px-3 rounded-full text-responsive-sm font-medium
          text-neutral-700 dark:text-neutral-300
          bg-neutral-200 dark:bg-neutral-800
          hover:bg-neutral-200 dark:hover:bg-neutral-700
          focus:outline-none
        "
      >
        {selected?.label || "Select"}
        <ChevronDown className="w-4 h-4 ml-2 text-neutral-500" />
      </button>

      {open && (
        <ul className="absolute z-2 mt-2 w-full 
        bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700
        rounded-2xl shadow-xl
        text-neutral-700 dark:text-neutral-300">
          {options.map((option) => (
            <li
              key={option.value}
              onClick={() => {
                onChange(option.value)
                setOpen(false)
              }}
              className={`
                px-4 py-2 cursor-pointer rounded-2xl 
                hover:bg-neutral-200 dark:hover:bg-neutral-800
                font-medium
              `}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
