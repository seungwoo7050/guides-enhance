// [Implementation 6] Server-rendered profile route
export default async function ProfilePage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  return <main><h1>{handle} 프로필</h1><p>URL의 동적 경로에서 읽은 사용자 이름입니다.</p></main>;
}
