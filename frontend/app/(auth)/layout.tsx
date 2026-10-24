export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <main className="auth-background flex min-h-screen items-center justify-center px-4 py-8">{children}</main>;
}
