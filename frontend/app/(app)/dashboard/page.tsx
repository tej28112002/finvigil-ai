import { createClient } from "@/lib/supabase/server";
import { WelcomeScreen } from "@/app/(app)/dashboard/dashboard-client";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const fullName = (user?.user_metadata?.full_name as string | undefined) ?? "";
  const email = user?.email ?? "";

  let firstName = "";
  if (fullName.trim()) {
    firstName = fullName.trim().split(/\s+/)[0] ?? "";
  } else if (email) {
    firstName = email.split("@")[0] ?? "";
  }
  if (firstName) {
    firstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);
  }

  return <WelcomeScreen userId={user?.id ?? ""} firstName={firstName} />;
}
