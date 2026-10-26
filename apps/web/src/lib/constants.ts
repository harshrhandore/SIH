import {
  LayoutDashboard,
  Upload,
  Search,
  ClipboardCheck,
  ChartNoAxesCombined,
  Layers,
  FileText,
  Settings,
  GraduationCap,
} from "lucide-react";

export const NAVIGATION = [
  [
    "/dashboard",
    "Institution ledger",
    LayoutDashboard,
    ["OPERATOR", "OFFICER"],
  ],
  ["/imports", "Imports", Upload, ["OPERATOR", "OFFICER"]],
  ["/students", "Student search", Search, ["OPERATOR", "OFFICER"]],
  [
    "/cases",
    "Verification cases",
    ClipboardCheck,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
  ["/oversight", "Institution oversight", Layers, ["ADMIN"]],
  [
    "/analytics",
    "Analytics",
    ChartNoAxesCombined,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
  ["/certificates", "Certificates", FileText, ["STUDENT"]],
  ["/career", "Career Copilot", GraduationCap, ["STUDENT"]],
  [
    "/architecture",
    "Architecture",
    Layers,
    ["OPERATOR", "OFFICER", "ADMIN", "STUDENT"],
  ],
  [
    "/settings/demo",
    "Demo controls",
    Settings,
    ["OPERATOR", "OFFICER", "ADMIN"],
  ],
] as const;
