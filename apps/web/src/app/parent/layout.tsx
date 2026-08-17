import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Parent Portal – EduCore',
};

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Parent Nav */}
      <header className="bg-white border-b sticky top-0 z-40 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              E
            </div>
            <span className="font-bold text-gray-900">EduCore</span>
            <span className="text-gray-300 text-sm">|</span>
            <span className="text-sm text-gray-500">Parent Portal</span>
          </div>
          <nav className="flex items-center gap-1">
            {[
              { href: '/parent', label: 'Dashboard' },
              { href: '/parent/children', label: 'My Children' },
            ].map(item => (
              <a
                key={item.href}
                href={item.href}
                className="px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
              >
                {item.label}
              </a>
            ))}
            <a
              href="/auth/login"
              className="ml-2 px-3 py-1.5 rounded-lg text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              Sign Out
            </a>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
