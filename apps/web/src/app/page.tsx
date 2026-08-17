import Link from 'next/link';
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  GraduationCap,
  ShieldCheck,
  Users,
} from 'lucide-react';

const modules = [
  { label: 'Admissions', value: '247', icon: Users },
  { label: 'Attendance', value: '94%', icon: CheckCircle2 },
  { label: 'Results', value: '61', icon: BarChart3 },
  { label: 'Timetable', value: 'Live', icon: CalendarDays },
];

const features = [
  'Student records, fees, attendance, results, and parent access in one place.',
  'Role-based staff dashboards for admin, bursar, teachers, parents, and students.',
  'Reports, audit logs, automations, documents, library, hostel, and transport modules.',
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
              <GraduationCap className="h-5 w-5" />
            </span>
            <div>
              <p className="text-base font-semibold">EduCore</p>
              <p className="text-xs text-slate-500">Enterprise School Management</p>
            </div>
          </div>
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Sign in
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.92fr_1.08fr] lg:px-8 lg:py-20">
        <div className="flex flex-col justify-center">
          <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
            <ShieldCheck className="h-4 w-4" />
            Running locally on your machine
          </div>
          <h1 className="max-w-3xl text-4xl font-bold leading-tight text-slate-950 sm:text-5xl">
            EduCore school operations, ready for daily work.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Manage academics, finance, staff, communication, reports, and student services from one
            connected workspace.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/auth/login"
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              Go to login
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-100"
            >
              Open dashboard
            </Link>
          </div>
          <div className="mt-8 space-y-3">
            {features.map((feature) => (
              <div key={feature} className="flex gap-3 text-sm text-slate-700">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-emerald-600" />
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xl shadow-slate-200/70">
          <div className="rounded-md border border-slate-200 bg-slate-950 p-4 text-white">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <p className="text-sm text-blue-200">Today</p>
                <p className="text-xl font-semibold">School Command Center</p>
              </div>
              <BookOpen className="h-8 w-8 text-blue-300" />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              {modules.map(({ label, value, icon: Icon }) => (
                <div key={label} className="rounded-md border border-white/10 bg-white/10 p-4">
                  <Icon className="h-5 w-5 text-blue-200" />
                  <p className="mt-4 text-2xl font-semibold">{value}</p>
                  <p className="text-sm text-slate-300">{label}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-md bg-white p-4 text-slate-900">
              <div className="flex items-center justify-between">
                <p className="font-semibold">Operational Snapshot</p>
                <span className="rounded-md bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">
                  Healthy
                </span>
              </div>
              <div className="mt-4 space-y-3">
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 w-10/12 rounded-full bg-blue-600" />
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 w-8/12 rounded-full bg-emerald-500" />
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 w-7/12 rounded-full bg-amber-500" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
