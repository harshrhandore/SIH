import Link from "next/link";
import { ChevronRight } from "lucide-react";

export function Breadcrumb({ path, home }: { path: string; home: string }) {
  const segments = path.split("/").filter(Boolean);
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      <Link href={home}>Workspace</Link>
      <ChevronRight size={13} aria-hidden="true" />
      <span aria-current="page">
        {segments[0]?.replaceAll("-", " ") || "Home"}
      </span>
    </nav>
  );
}
