"use client"
import { useState, useEffect, useRef  } from "react"
import { Settings2 } from "lucide-react"
import Dropdown from "@/components/Dropdown"

export default function SettingsMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const [temperature, setTemperature] = useState(0.00645)
  const [model, setModel] = useState("mistralai/Mistral-7B-Instruct-v0.1")
  const [tone, setTone] = useState("neutral")
  const menuRef = useRef<HTMLDivElement>(null)

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

useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    } else {
      document.removeEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [isOpen])

  // ✅ Sync config
  useEffect(() => {
    const config = { temperature, model, tone }
    fetch("http://localhost:8000/set-config", {
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

  useEffect(() => {
    const config = { temperature, model, tone }
    fetch("http://localhost:8000/set-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
    }, [temperature, model, tone])

  return (
    <div className="absolute top-3 right-3">
      <div className="flex justify-end mb-3">
        <button
          className="p-2 rounded-xl flex items-center gap-2 
          text-neutral-700 dark:text-neutral-300 font-semibold 
          hover:bg-neutral-200 dark:hover:bg-neutral-800"
          onClick={() => setIsOpen(!isOpen)}
        >
          <Settings2 size={20} />
        </button>
      </div>

      {isOpen && (
        <div className="px-2 py-2 pt-3  bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-3xl shadow-lg w-72">
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
          <div className="mb-1">
            <div className="px-3 pb-3 text-sm font-medium flex justify-between">
                <label className="block text-neutral-800 dark:text-neutral-200">
                    Response Style
                </label>
                <p className="block text-neutral-500 dark:text-neutral-500">{getTemperatureLabel(temperature)}</p>
            </div>
            {/* Background track */}
            <div className="relative w-full h-7 rounded-full bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 hover:dark:bg-neutral-700">
                <div
                className="absolute h-7 rounded-full bg-green-500"
                style={{ width: `${(temperature + 0.05) * 200}%` }}
                />

                {/* Transparent slider overlaid */}
                <input
                type="range"
                min="0.00645"
                max="0.45"
                step="0.08871"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="absolute top-0 left-0 w-full h-3 opacity-0 cursor-pointer"
                />
            </div>
            <style jsx>{`
                input[type='range']::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 0;
                height: 0;
                }
                input[type='range']::-moz-range-thumb {
                width: 0;
                height: 0;
                background: transparent;
                border: none;
                }
            `}</style>
          </div>
        </div>
      )}
    </div>
  )
}
