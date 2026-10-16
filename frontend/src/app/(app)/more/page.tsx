import { redirect } from "next/navigation";

/** Everything that used to be listed here is now in the main navigation. */
export default function MorePage() {
  redirect("/home");
}
