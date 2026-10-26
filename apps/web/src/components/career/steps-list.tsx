import type { components } from "@/lib/generated/api";

export function StepsList({
  steps,
}: {
  steps: components["schemas"]["Step"][];
}) {
  return (
    <div>
      <h3>Recommended steps</h3>
      <ol className="career-steps">
        {steps.map((step) => (
          <li className="finding" key={step.priority}>
            <h4>{step.action}</h4>
            <p>
              {step.reason} · {step.estimated_weeks}{" "}
              {step.estimated_weeks === 1 ? "week" : "weeks"}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}
