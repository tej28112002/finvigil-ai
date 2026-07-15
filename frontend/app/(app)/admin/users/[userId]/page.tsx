import { UserDetailClient } from "./user-detail-client";

export default async function AdminUserDetailPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = await params;
  return <UserDetailClient userId={userId} />;
}
