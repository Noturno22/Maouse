import { AdminArea } from "@/components/admin-area";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Painel — Mãouse",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return <AdminArea />;
}