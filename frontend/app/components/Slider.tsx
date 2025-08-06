import React from "react";
import styles from "./Slider.module.css";

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  displayValue?: string;
}

const Slider: React.FC<SliderProps> = ({
  label,
  value,
  min,
  max,
  step,
  onChange,
  displayValue,
}) => (
  <div>
    <div className="pb-3 text-responsive-lg font-medium flex justify-between">
      <label className="block text-neutral-800 dark:text-neutral-200">
        {label}
      </label>
      <p className="block text-neutral-500 dark:text-neutral-500">
        {displayValue ?? value}
      </p>
    </div>
    <div className="relative w-full h-9 rounded-xl bg-neutral-200 dark:bg-neutral-800 hover:bg-neutral-200 hover:dark:bg-neutral-700">
      <div
        className="absolute h-9 rounded-xl bg-green-500"
        style={{ width: `${((value - min) / (max - min)) * 100}%` }}
      />
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="absolute top-0 left-0 w-full h-9 opacity-0 cursor-pointer"
      />
    </div>
  </div>
);

export default Slider;