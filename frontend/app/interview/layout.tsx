import '../globals.css'

export const metadata = {
  title: 'Interview - HireHelper',
  description: 'AI-Powered Interview Session'
}

export default function InterviewLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}
