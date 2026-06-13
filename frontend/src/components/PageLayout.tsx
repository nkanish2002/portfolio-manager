import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import type { ReactNode } from 'react';
import { usePortfolioStore } from '../store';

interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [portfolioDropdownOpen, setPortfolioDropdownOpen] = useState(false);
  const { portfolios, fetchPortfolios } = usePortfolioStore();

  // Fetch portfolios on mount
  useEffect(() => {
    if (portfolios.length === 0) {
      fetchPortfolios();
    }
  }, [portfolios.length, fetchPortfolios]);

  const navItems = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/positions', label: 'Positions' },
    { path: '/trades', label: 'Trade Audit' },
    { path: '/analytics', label: 'Analytics' },
    { path: '/settings', label: 'Settings' },
  ];

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/');

  const handlePortfolioSelect = (id: string) => {
    // Determine which page we're on and navigate with portfolio
    const currentPath = location.pathname;
    if (currentPath === '/dashboard' || currentPath === '/') {
      navigate(`/dashboard/${id}`);
    } else {
      // For other pages, set the portfolio and navigate there
      const pathWithPortfolio = `/positions/${id}`;
      navigate(pathWithPortfolio);
    }
    setPortfolioDropdownOpen(false);
  };

  // Get current portfolio display name from URL
  const currentPortfolioName = (() => {
    const match = location.pathname.match(/\/dashboard\/([^/]+)|\/positions\/([^/]+)/);
    if (match) {
      const id = match[1] || match[2];
      const portfolio = portfolios.find((p) => p.id === id);
      return portfolio ? portfolio.name : id.substring(0, 8);
    }
    return null;
  })();

  return (
    <div className="min-h-screen bg-black text-white pb-8 md:pb-0">
      {/* Navigation */}
      <nav className="bg-black/95 backdrop-blur border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link
              to="/dashboard"
              className="text-lg font-bold text-white hover:text-gray-400 transition-colors"
            >
              Portfolio Manager
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-1">
              {/* Portfolio Dropdown */}
              <div className="relative ml-2 mr-4">
                <button
                  onClick={() => setPortfolioDropdownOpen(!portfolioDropdownOpen)}
                  className="px-3 py-2 rounded-none text-sm font-medium transition-colors min-w-[44px] min-h-[44px] flex items-center gap-2 text-slate-400 hover:text-white hover:bg-slate-800/50 border border-slate-800"
                >
                  <span className="truncate max-w-[120px]">
                    {currentPortfolioName || 'Select Portfolio'}
                  </span>
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {portfolioDropdownOpen && (
                  <>
                    {/* Backdrop */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setPortfolioDropdownOpen(false)}
                    />
                    {/* Dropdown */}
                    <div className="absolute left-0 top-full mt-1 w-72 bg-gray-900 border border-slate-800 rounded-none z-50 max-h-80 overflow-y-auto">
                      {portfolios.length === 0 ? (
                        <div className="px-4 py-3 text-slate-500 text-sm">No portfolios</div>
                      ) : (
                        portfolios.map((portfolio) => (
                          <button
                            key={portfolio.id}
                            onClick={() => handlePortfolioSelect(portfolio.id)}
                            className={`w-full px-4 py-3 text-left text-sm transition-colors border-b border-slate-800/50 last:border-b-0 ${
                              currentPortfolioName === portfolio.name
                                ? 'bg-slate-800 text-white'
                                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                            }`}
                          >
                            <div className="font-medium truncate">{portfolio.name}</div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              {portfolio.position_count} positions · {portfolio.currency}
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </>
                )}
              </div>

              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 rounded-none text-sm font-medium transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center ${
                    isActive(item.path)
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-none text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Toggle menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {mobileMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-800 bg-black/95 backdrop-blur">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {/* Mobile Portfolio Selector */}
              <div className="px-3 py-2 border-b border-slate-800 mb-1">
                <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Portfolios</div>
                {portfolios.length === 0 ? (
                  <div className="text-slate-600 text-sm py-1">No portfolios</div>
                ) : (
                  portfolios.map((portfolio) => (
                    <button
                      key={portfolio.id}
                      onClick={() => handlePortfolioSelect(portfolio.id)}
                      className={`w-full px-3 py-2 text-left text-sm transition-colors rounded-none mb-1 ${
                        currentPortfolioName === portfolio.name
                          ? 'bg-slate-800 text-white'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="font-medium truncate">{portfolio.name}</div>
                      <div className="text-xs text-slate-600">
                        {portfolio.position_count} positions · {portfolio.currency}
                      </div>
                    </button>
                  ))
                )}
              </div>

              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-3 rounded-none text-base font-medium transition-colors min-h-[44px] flex items-center ${
                    isActive(item.path)
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
        {children}
      </main>
    </div>
  );
}
