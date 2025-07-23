import React from "react";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}

const Toggle: React.FC<ToggleProps> = ({ checked, onChange, label }) => (
  <div className="flex justify-between items-center">
    {label && (
      <label className="px-3 text-responsive-sm font-medium text-neutral-800 dark:text-neutral-200">
        {label}
      </label>
    )}
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`w-12 h-7 flex items-center rounded-full
        ${checked ? "bg-green-500 hover:bg-green-600" : "hover:bg-neutral-200 hover:dark:bg-neutral-700 bg-neutral-100 dark:bg-neutral-800"}`}
      aria-pressed={checked}
    >
      <div
        className={`w-6 h-6 bg-white rounded-full transition-transform duration-300 ease-in-out
          ${checked ? "translate-x-5.5" : "translate-x-0.5"}`}
      />
    </button>
  </div>
);

export default Toggle;