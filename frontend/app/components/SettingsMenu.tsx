"use client"
import { useState, useEffect, useRef  } from "react"
import { Settings2, X, Palette } from "lucide-react"
import Dropdown from "@/components/Dropdown"
import Slider from "@/components/Slider"

interface SettingsMenuProps {
  open: boolean;
  onClose: () => void;
}

type TabKey = "general" | "personalization"

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

  useEffect(() => {
    const config = { temperature, model, tone }
    fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/set-config`, {
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

  const [theme, setTheme] = useState<"light" | "dark">("light")
  const [nickname, setNickname] = useState<string>("")

  useEffect(() => {
    const storedTheme = (localStorage.getItem("theme") as "light" | "dark") || null
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    const initialTheme = storedTheme ?? (prefersDark ? "dark" : "light")
    setTheme(initialTheme)

    const storedName = localStorage.getItem("nickname") || ""
    setNickname(storedName) 
  }, [])

  useEffect(() => {
    const root = document.documentElement
    if (theme === "dark") {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
    localStorage.setItem("theme", theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem("nickname", nickname)
  }, [nickname])

  const [activeTab, setActiveTab] = useState<TabKey>("general")
  const modalRef = useRef<HTMLDivElement>(null)

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
      <div className="absolute inset-0 bg-black/20 backdrop-blur-[6px]" />
      <div ref={modalRef} className="relative bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 w-full max-w-xl mx-auto z-10">
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-800">
          <h2 className="text-responsive-2xl font-semibold text-neutral-800 dark:text-neutral-100">Settings</h2>
        </div>
        <div className="flex min-h-[420px]">
          <nav className="w-48 border-r- border-neutral-200 dark:border-neutral-800 p-3">
            <button 
              onClick={() => setActiveTab("general")}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left mb-1 transition
                ${activeTab === "general" 
                  ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100" 
                  : "text-neutral-700dark:text-neutral-300 hover:bg-neutral-100/70 dark:hover:bg-neutral-800/70"
                }`}
            >
              <Settings2 size={10} />
              <span>General</span>
            </button>
            <button 
              onClick={() => setActiveTab("personalization")}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left mb-1 transition
                ${activeTab === "personalization" 
                  ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100" 
                  : "text-neutral-700dark:text-neutral-300 hover:bg-neutral-100/70 dark:hover:bg-neutral-800/70"
                }`}
            >
              <Palette size={10} />
              <span>Personalization</span>
            </button>
          </nav>
          <div className="flex-1 p-6">
            {/* Settings form content */}
            {activeTab === "general" && (
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
            )}
            {activeTab === "personalization" && (
              <div className="flex flex-col gap-7">
                <div>
                  <label className="block text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">
                    Theme
                  </label>
                  <div className="inline-flex rounded-xl border">
                    <button className={`px-4 py-2 text-sm transition ${
                      theme === "light"
                        ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                        : "bg-transparent text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                    }`}
                      onClick={() => setTheme("light")}
                    >
                      Light
                    </button>
                    <button className={`px-4 py-2 text-sm transition ${
                      theme === "dark"
                        ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                        : "bg-transparent text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                    }`}
                      onClick={() => setTheme("dark")}
                    >
                      Dark
                    </button>
                  </div>
                </div>
                <div>
                  <label htmlFor="nickname"
                    className="block text-sm font-medium text-neutral-800 darl:text-neutral-200 mb-2"
                  >
                    Nickname
                  </label>
                  <input
                    id="nickname"
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral900 text-neutral-900 dark:text-neutral-100 px-4 py-2 outline-none focus:ring-none"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}