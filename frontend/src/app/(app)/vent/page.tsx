import { redirect } from "next/navigation";

/** Vent now lives inside Check in, as its second tab. Old links land there. */
export default function VentPage() {
  redirect("/check-in?tab=vent");
}
