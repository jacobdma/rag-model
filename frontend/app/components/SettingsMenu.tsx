"use client"
import { useState, useEffect, useRef  } from "react"
import { Settings2, X } from "lucide-react"
import Dropdown from "@/components/Dropdown"
import Slider from "@/components/Slider"
import Toggle from "@/components/Toggle"

interface SettingsMenuProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsMenu({
  open,
  onClose,
}: SettingsMenuProps) {
  const [temperature, setTemperature] = useState(0.00645)
  const [model, setModel] = useState("mistralai/Mistral-7B-Instruct-v0.1")
  const [tone, setTone] = useState("neutral")

  const temperatureStops = [
    { value: 0.00645, label: "Precise" },
    { value: 0.09516, label: "Technical" },
    { value: 0.18387, label: "Focused" },
    { value: 0.27258, label: "Balanced" },
    { value: 0.36129, label: "Flexible" },
    { value: 0.45, label: "Creative" }
  ]

  function getTemperatureLabel(value: number): string {
    const match = temperatureStops.find((stop) => stop.value === value)
    return match ? match.label : "Unknown"
  }

  // ✅ Sync config
  useEffect(() => {
    const config = { temperature, model, tone }
    fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:8000/set-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
  }, [temperature, model, tone])

  const toneOptions = [
    { label: "Formal", value: "formal" },
    { label: "Neutral", value: "neutral" },
    { label: "Casual", value: "casual" },
  ]

  const modelOptions = [
      { label: "Mistral", value: "mistralai/Mistral-7B-Instruct-v0.1"},
  ]

  const modalRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (open && modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick)
    }
    return () => document.removeEventListener("mousedown", handleClick)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Blurred overlay */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[6px]" />
      <div ref={modalRef} className="relative bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-auto p-8 z-10">
        <button
          className="absolute top-4 right-4 text-neutral-400 hover:text-red-500 text-responsive-xl font-bold rounded-full p-1 focus:outline-none"
          onClick={onClose}
          title="Close"
        >
          <X />
        </button>
        
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100 mb-6">
          Settings
        </h2>
        
        {/* Settings form content */}
        <div className="flex flex-col gap-7">
          {/* Tone Selector */}
          <Dropdown
            label="Tone"
            options={toneOptions}
            value={tone}
            onChange={setTone}
          />

          {/* Model Selector */}
          <Dropdown
              label="Model"
              options={modelOptions}
              value={model}
              onChange={setModel}
          />

          {/* Temperature Slider */}
          <Slider
            label="Response Style"
            value={temperature}
            min={0.00645}
            max={0.45}
            step={0.08871}
            onChange={setTemperature}
            displayValue={getTemperatureLabel(temperature)}
          />
        </div>
      </div>
    </div>
  )
}