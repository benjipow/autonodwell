import { FloorPlan } from './Drawings'

/** Line-drawn floor plan for a model. */
export function ModelMedia({ planKey }: { planKey: string }) {
  return (
    <div className="model-media">
      <FloorPlan planKey={planKey} className="plan" />
    </div>
  )
}
