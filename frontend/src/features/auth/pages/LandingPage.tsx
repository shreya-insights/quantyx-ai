import { Link } from "react-router-dom";
import { ROUTES } from "@/utils/constants";

const features = [
  { icon: "📊", title: "SQL-First Analytics Engine", desc: "Revenue trends with LAG() window functions, MoM growth, cohort retention — all powered by optimized MySQL 8.0 queries." },
  { icon: "🎯", title: "RFM Customer Segmentation",  desc: "Segment customers into Champions, Loyal, At Risk using multi-level CTEs with NTILE(5) scoring — fully automated." },
  { icon: "🛡️", title: "Fraud Detection Engine",      desc: "5-rule engine: velocity checks, amount spikes (3× rolling avg), location anomalies, duplicate tx, and night patterns." },
  { icon: "💻", title: "Analyst Query Lab",           desc: "Write SQL directly on your live data with Monaco editor. Pre-built templates, save queries, instant results." },
  { icon: "📈", title: "Cohort Retention Analysis",   desc: "Visualize user retention month-by-month with PERIOD_DIFF cohort matrices. Understand churn at a glance." },
  { icon: "🏢", title: "Multi-Tenant SaaS",           desc: "True company-level isolation. RBAC with admin, analyst, and viewer roles. Three subscription tiers." },
];

const plans = [
  { name: "Starter",    price: "Free",  period: "forever",  features: ["1 user", "10K tx/month", "Core analytics", "KPI dashboard"],                                       cta: "Get Started", popular: false, href: ROUTES.REGISTER },
  { name: "Growth",     price: "$49",   period: "/month",   features: ["10 users", "500K tx/month", "Fraud detection", "Query Lab", "CSV exports", "RFM segmentation"],     cta: "Start Trial", popular: true,  href: ROUTES.REGISTER },
  { name: "Enterprise", price: "$199",  period: "/month",   features: ["Unlimited users", "Unlimited tx", "Custom reports", "PDF export", "White-label", "Priority SLA"],   cta: "Contact Sales", popular: false, href: ROUTES.REGISTER },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="border-b border-slate-800/60 backdrop-blur-sm sticky top-0 z-40 bg-slate-950/90">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-sm font-bold shadow-lg shadow-blue-900/40">Q</div>
            <span className="font-bold text-lg">Quantyx AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to={ROUTES.LOGIN} className="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5">Sign In</Link>
            <Link to={ROUTES.REGISTER} className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-medium transition-colors">Get Started Free</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-6 py-28 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-950/20 to-transparent pointer-events-none" />
        <div className="relative max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-blue-900/40 border border-blue-700/40 rounded-full px-4 py-1.5 text-sm text-blue-300 mb-8">
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
            Multi-Tenant Fintech Analytics SaaS
          </div>
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6">
            Turn Financial Data Into{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-violet-400">
              Real-Time Intelligence
            </span>
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            SQL-first analytics engine with fraud detection, RFM segmentation, cohort analysis,
            and a live SQL Query Lab — built for fintech teams that think in data.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to={ROUTES.REGISTER} className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-colors shadow-lg shadow-blue-900/30">
              Start Free →
            </Link>
            <Link to={ROUTES.LOGIN} className="border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white px-8 py-3.5 rounded-xl font-semibold text-lg transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y border-slate-800 py-10">
        <div className="max-w-4xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { v: "10+",   l: "Advanced SQL Queries" },
            { v: "5",     l: "Fraud Detection Rules" },
            { v: "3",     l: "Subscription Tiers" },
            { v: "100%",  l: "Multi-Tenant Isolated" },
          ].map((s) => (
            <div key={s.l}>
              <div className="text-3xl font-bold text-blue-400">{s.v}</div>
              <div className="text-sm text-slate-400 mt-1">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">Enterprise-Grade Analytics for Fintech</h2>
          <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
            Every feature powered by production-quality SQL — window functions, CTEs, partitioned tables, covering indexes.
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => (
              <div key={f.title} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-600 transition-colors group">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-semibold text-lg mb-2 group-hover:text-blue-400 transition-colors">{f.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="px-6 py-20 bg-slate-900/50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3">Simple, Transparent Pricing</h2>
          <p className="text-slate-400 text-center mb-12">Start free, scale as you grow.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div key={plan.name} className={`bg-slate-900 rounded-2xl p-6 flex flex-col border-2 ${plan.popular ? "border-blue-500 shadow-xl shadow-blue-900/20" : "border-slate-800"}`}>
                {plan.popular && (
                  <span className="inline-block bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full mb-4 w-fit">Most Popular</span>
                )}
                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                <div className="mb-6">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-slate-400 text-sm">{plan.period}</span>
                </div>
                <ul className="space-y-2 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                      <span className="text-emerald-400 flex-shrink-0">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <Link to={plan.href} className="w-full text-center bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-xl font-medium transition-colors">
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-8 text-center text-slate-500 text-sm">
        <p>© 2026 Quantyx AI · Built with FastAPI · MySQL 8.0 · Vite · React</p>
      </footer>
    </div>
  );
}
